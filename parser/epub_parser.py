"""Main EPUB parser for Orthodox Study Bible."""
import re
from pathlib import Path
from lxml import etree
from bs4 import BeautifulSoup, NavigableString
from typing import Optional

from .models import Book, Passage, Annotation, PatristicSource, AnnotationMarker
import copy

# Namespace for OPF files
OPF_NS = {'opf': 'http://www.idpf.org/2007/opf'}

# Books that mark the start of New Testament
NT_START_ORDER = 50  # Matthew is RW_50

# CSS classes that act as structural boundaries (stop text scanning)
# These elements separate sections and should not be absorbed into verse text
BOUNDARY_CLASSES = frozenset({
    'psalm',      # Psalm chapter headers: <p class="psalm">Psalm 16 (17)</p>
    'sub1',       # Section headers: <p class="sub1">The Garden of Eden</p>
    'sub2',       # Sub-section headers
})


class OSBParser:
    """Parser for Orthodox Study Bible EPUB."""

    def __init__(self, epub_dir: str):
        self.epub_dir = Path(epub_dir)
        self.oebps_dir = self.epub_dir / "OEBPS"

        # Parsed data
        self.books: dict[str, Book] = {}
        self.passages: dict[str, Passage] = {}
        self.annotations: dict[str, Annotation] = {}
        self.patristic_sources: dict[str, PatristicSource] = {}

        # Cross-reference data (intermediate)
        self._cross_refs: dict[str, dict] = {}  # fcross_id -> {source_id, targets, text}
        self._verse_to_cross_ref: dict[str, str] = {}  # verse_id -> fcross_id

        # Book abbreviation to book_id mapping
        self._abbrev_to_book: dict[str, str] = {}

    def _is_boundary(self, element) -> bool:
        """Check if element is a structural boundary that should stop text scanning.

        Boundaries include:
        - Elements with boundary CSS classes (psalm, sub1, sub2)
        - Article divs with gray background styling
        """
        if not hasattr(element, 'get'):
            return False

        # Check CSS classes
        classes = element.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        if set(classes) & BOUNDARY_CLASSES:
            return True

        # Check for article divs (inline topical articles)
        # These use <div style="background-color: gray;">
        if hasattr(element, 'name') and element.name == 'div':
            style = element.get('style', '')
            if 'background-color' in style and 'gray' in style:
                return True

        return False

    def _collect_variant_markers(self, soup) -> dict[str, list[str]]:
        """Pre-collect variant marker IDs before they get stripped.

        Returns a dict mapping verse_id -> [fvar_ids] by finding the nearest
        preceding verse marker for each variant link.
        """
        verse_to_variants = {}

        # Find all variant markers
        for link in soup.find_all('a', href=lambda h: h and 'variant.html#fvar' in h):
            match = re.search(r'#(fvar\d+)', link.get('href', ''))
            if not match:
                continue
            fvar_id = match.group(1)

            # Find nearest preceding verse marker by walking up and back
            # Look for an element with an ID matching the verse pattern
            verse_pattern = re.compile(r'^[A-Za-z0-9]+_vchap\d+-\d+$')

            # Walk backwards through previous elements to find verse marker
            current = link
            verse_id = None
            while current:
                # Check if current element has a verse ID
                if hasattr(current, 'get') and current.get('id'):
                    elem_id = current.get('id')
                    if verse_pattern.match(elem_id):
                        verse_id = elem_id
                        break
                # Check parent's ID
                if current.parent and hasattr(current.parent, 'get') and current.parent.get('id'):
                    parent_id = current.parent.get('id')
                    if verse_pattern.match(parent_id):
                        verse_id = parent_id
                        break
                # Check all previous siblings and their descendants
                prev = current.find_previous(id=verse_pattern)
                if prev:
                    verse_id = prev.get('id')
                    break
                current = current.parent

            if verse_id:
                if verse_id not in verse_to_variants:
                    verse_to_variants[verse_id] = []
                verse_to_variants[verse_id].append(fvar_id)

        return verse_to_variants

    def _extract_articles(self, soup, book: 'Book') -> dict[str, list[str]]:
        """Extract inline topical articles from book HTML.

        Articles are wrapped in <div style="background-color: gray;"> and contain:
        - <p class="ct" id="article-slug"> - Title with spaced letters
        - <p class="sub1"> - Section headers
        - <p class="tx1">, <p class="tx">, <p class="ext"> - Body text

        Returns a dict mapping following_verse_id -> [article_ids] so passages
        can be updated with their linked articles.
        """
        verse_to_articles = {}
        verse_pattern = re.compile(r'^[A-Za-z0-9]+_vchap\d+-\d+$')

        # Find all article divs
        for div in soup.find_all('div', style=lambda s: s and 'background-color' in s and 'gray' in s):
            # Get article ID from the <p class="ct" id="..."> element
            title_p = div.find('p', class_='ct')
            if not title_p:
                continue

            article_id = title_p.get('id')
            if not article_id:
                # Generate an ID from the title text if none exists
                title_text = title_p.get_text(strip=True)
                article_id = re.sub(r'[^a-z0-9]+', '_', title_text.lower()).strip('_')[:30]

            # Extract title - clean up spaced letters (T H E  H O L Y -> THE HOLY)
            # The source uses: single spaces between letters, double nbsp or <br/> between words
            # Use separator='  ' to preserve br tags as double spaces (word boundaries)
            raw_title = title_p.get_text(separator='  ', strip=True)
            # Mark word boundaries (double space or double nbsp → marker)
            clean_title = re.sub(r'[\s\u00a0]{2,}', '||', raw_title)
            # Remove single spaces between letters within words
            clean_title = re.sub(r'([A-Z])[\s\u00a0](?=[A-Z])', r'\1', clean_title)
            # Restore word boundaries
            clean_title = clean_title.replace('||', ' ').strip()

            # Extract full article HTML and text
            article_html = str(div)
            article_text = self._clean_article_text(div, clean_title)

            # Find the next verse marker AFTER this article div
            following_verse_id = None
            for sibling in div.find_all_next(id=verse_pattern):
                following_verse_id = sibling.get('id')
                break

            if not following_verse_id:
                # Article at end of file with no following verse - skip or link to last verse
                continue

            # Create verse_display from the following verse ID
            # e.g., "Gen_vchap1-1" -> "1:1"
            verse_match = re.match(r'[A-Za-z0-9]+_vchap(\d+)-(\d+)', following_verse_id)
            verse_display = f"{verse_match.group(1)}:{verse_match.group(2)}" if verse_match else ""

            # Create the annotation
            annotation = Annotation(
                id=article_id,
                type='article',
                passage_ids=[following_verse_id],
                verse_display=verse_display,
                text=article_text,
                html=article_html,
                patristic_citations=[],
                scripture_refs=self._extract_scripture_refs_from_html(div)
            )

            self.annotations[article_id] = annotation

            # Track which verse this article is linked to
            if following_verse_id not in verse_to_articles:
                verse_to_articles[following_verse_id] = []
            verse_to_articles[following_verse_id].append(article_id)

        return verse_to_articles

    def _clean_article_text(self, div, title: str) -> str:
        """Extract clean text from article div, preserving structure and <i>/<b> tags."""
        parts = [title, ""]  # Start with cleaned title

        for p in div.find_all('p'):
            p_class = p.get('class', [])
            if isinstance(p_class, str):
                p_class = p_class.split()

            if 'ct' in p_class:
                continue  # Skip title, we already have it

            text = self._clean_text(self._extract_styled_text(p))
            if not text:
                continue

            if 'sub1' in p_class:
                # Section header - add blank line before
                parts.append("")
                parts.append(text.upper() if text == text.lower() else text)
            elif 'ext' in p_class:
                # Extended quote - indent
                parts.append(f"    {text}")
            else:
                parts.append(text)

        return "\n".join(parts).strip()

    def _extract_scripture_refs_from_html(self, element) -> list[str]:
        """Extract scripture reference IDs from links in HTML element."""
        refs = []
        verse_pattern = re.compile(r'([A-Za-z0-9]+_vchap\d+-\d+)')

        for link in element.find_all('a', href=True):
            href = link.get('href', '')
            # Look for verse IDs in the href (e.g., "Genesis.html#Gen_vchap1-26")
            match = verse_pattern.search(href)
            if match:
                refs.append(match.group(1))

        return refs

    def _collect_annotation_markers(self, soup) -> dict[str, list[AnnotationMarker]]:
        """Collect all annotation markers with their preceding context before stripping.

        Returns a dict mapping verse_id -> list of AnnotationMarker objects.
        Each marker includes the annotation ID, type, and up to 40 chars of preceding text.
        """
        verse_to_markers = {}
        verse_pattern = re.compile(r'^[A-Za-z0-9]+_vchap\d+-\d+$')

        # Define marker types and their href patterns
        marker_configs = [
            ('study', r'study\d+\.html#(f\d+)', lambda h: 'study' in h and '#f' in h and 'fx' not in h),
            ('liturgical', r'x-liturgical\.html#(fx\d+)', lambda h: 'liturgical' in h and '#fx' in h),
            ('variant', r'variant\.html#(fvar\d+)', lambda h: 'variant.html#fvar' in h),
            ('citation', r'citation\.html#(fcit\d+)', lambda h: 'citation.html#fcit' in h),
            ('cross_ref', r'crossReference\.html#(fcross\d+)', lambda h: 'crossReference.html#fcross' in h),
        ]

        for marker_type, id_pattern, href_filter in marker_configs:
            for link in soup.find_all('a', href=lambda h: h and href_filter(h)):
                href = link.get('href', '')
                match = re.search(id_pattern, href)
                if not match:
                    continue

                marker_id = match.group(1)

                # For cross-refs with single-letter text (a, b, c), still collect them
                # They'll be stripped but we want the position data
                link_text = link.get_text(strip=True)

                # Get preceding text - walk backwards through text nodes
                preceding_text = self._get_preceding_text(link, max_chars=40)

                # Find the verse this marker belongs to
                verse_id = self._find_verse_for_element(link, verse_pattern)

                if verse_id:
                    if verse_id not in verse_to_markers:
                        verse_to_markers[verse_id] = []

                    marker = AnnotationMarker(
                        id=marker_id,
                        type=marker_type,
                        preceding=preceding_text
                    )
                    verse_to_markers[verse_id].append(marker)

        return verse_to_markers

    def _get_preceding_text(self, element, max_chars: int = 40) -> str:
        """Extract up to max_chars of text immediately before an element.

        Walks backwards through text nodes to collect preceding content.
        """
        text_parts = []
        chars_collected = 0

        # Start from the element and walk backwards
        current = element

        while current and chars_collected < max_chars:
            # Check previous siblings first
            prev_sibling = current.previous_sibling

            while prev_sibling and chars_collected < max_chars:
                if isinstance(prev_sibling, NavigableString):
                    text = str(prev_sibling)
                    # Clean up the text
                    text = re.sub(r'\s+', ' ', text)
                    if text.strip():
                        text_parts.insert(0, text)
                        chars_collected += len(text)
                elif hasattr(prev_sibling, 'get_text'):
                    text = prev_sibling.get_text()
                    text = re.sub(r'\s+', ' ', text)
                    if text.strip():
                        text_parts.insert(0, text)
                        chars_collected += len(text)
                prev_sibling = prev_sibling.previous_sibling

            # Move to parent and continue
            current = current.parent
            if current and hasattr(current, 'name') and current.name in ['body', 'html', None]:
                break

        # Join text parts and use same cleaning as verse text
        result = ''.join(text_parts)
        result = self._clean_text(result)

        # Take last max_chars characters
        if len(result) > max_chars:
            result = result[-max_chars:]
            # Try to break at a word boundary
            space_idx = result.find(' ')
            if space_idx > 0 and space_idx < 10:
                result = result[space_idx + 1:]

        return result

    def _find_verse_for_element(self, element, verse_pattern) -> Optional[str]:
        """Find the verse ID that contains or precedes this element."""
        # Walk backwards through previous elements to find verse marker
        current = element
        while current:
            # Check if current element has a verse ID
            if hasattr(current, 'get') and current.get('id'):
                elem_id = current.get('id')
                if verse_pattern.match(elem_id):
                    return elem_id
            # Check parent's ID
            if current.parent and hasattr(current.parent, 'get') and current.parent.get('id'):
                parent_id = current.parent.get('id')
                if verse_pattern.match(parent_id):
                    return parent_id
            # Check all previous siblings and their descendants
            prev = current.find_previous(id=verse_pattern)
            if prev:
                return prev.get('id')
            current = current.parent
        return None

    def _strip_variant_markers(self, soup):
        """Remove variant text marker elements before text extraction.

        Two types of markers are stripped:
        1. Variant markers: <sup><a href="variant.html#fvarN">a</a></sup>
        2. Cross-ref variant markers: <sup><a href="crossReference.html#fcrossN">a</a></sup>
           where the link text is a single letter (a, b, c...)

        These indicate textual variants (NU-Text, M-Text) and should not appear
        in the extracted verse text.
        """
        # Strip variant.html links
        for link in soup.find_all('a', href=lambda h: h and 'variant.html' in h):
            parent = link.parent
            if parent and parent.name == 'sup':
                parent.decompose()
            else:
                link.decompose()

        # Strip other single-letter reference markers (cross-refs, translation, background notes)
        marker_patterns = ['crossReference.html#fcross', 'translation.html#ftran', 'background.html#fback']
        for link in soup.find_all('a', href=lambda h: h and any(p in h for p in marker_patterns)):
            text = link.get_text(strip=True)
            if len(text) == 1 and text.isalpha():
                parent = link.parent
                if parent and parent.name == 'sup':
                    parent.decompose()
                else:
                    link.decompose()

    def parse_all(self):
        """Parse all content from the EPUB."""
        print("Parsing book metadata...")
        self._parse_manifest()

        print("Parsing patristic sources...")
        self._parse_patristic_sources()

        print("Parsing cross-references...")
        self._parse_cross_references()

        print("Parsing study notes...")
        self._parse_study_notes()

        print("Parsing liturgical notes...")
        self._parse_liturgical_notes()

        print("Parsing variant notes...")
        self._parse_variant_notes()

        print("Parsing citation notes...")
        self._parse_citation_notes()

        print("Parsing biblical passages...")
        self._parse_passages()

        print(f"Parsed: {len(self.books)} books, {len(self.passages)} passages, "
              f"{len(self.annotations)} annotations, {len(self.patristic_sources)} sources")

    def _parse_manifest(self):
        """Parse content.opf to extract book metadata."""
        opf_path = self.oebps_dir / "content.opf"
        tree = etree.parse(str(opf_path))
        root = tree.getroot()

        # Find all biblical book items (RW_XX_BookName pattern)
        manifest = root.find('opf:manifest', OPF_NS)

        book_pattern = re.compile(r'^RW_(\d+)_(.+?)(\d*)$')
        book_files: dict[str, list[tuple[int, str]]] = {}  # book_id -> [(order, filename)]

        for item in manifest.findall('opf:item', OPF_NS):
            item_id = item.get('id', '')
            href = item.get('href', '')

            match = book_pattern.match(item_id)
            if match and href.endswith('.html'):
                order = int(match.group(1))
                book_name = match.group(2)
                file_suffix = match.group(3)  # empty or "1", "2" for continuation files

                # Skip TOC files - they're navigation, not content
                if book_name.lower().endswith('_toc') or '_toc' in book_name.lower():
                    continue

                # Normalize book_id
                book_id = book_name.lower().replace('_', '')

                if book_id not in book_files:
                    book_files[book_id] = []

                # Sort key: main file first, then numbered continuations
                sort_key = 0 if not file_suffix else int(file_suffix)
                book_files[book_id].append((sort_key, href, order, book_name))

        # Create Book objects
        # Special handling for multi-text files (like Daniel.html containing Susanna, Daniel, Bel)
        MULTI_ABBREV_NAMES = {
            'Sus': 'Susanna',
            'Dan': 'Daniel',
            'Bel': 'Bel and the Dragon',
        }

        for book_id, files in book_files.items():
            files.sort(key=lambda x: x[0])  # Sort by file suffix

            first_file = files[0]
            order = first_file[2]
            display_name = first_file[3].replace('_', ' ')

            # Determine testament
            testament = "new" if order >= NT_START_ORDER else "old"

            # Extract ALL abbreviations from all files in this book
            abbreviations = []
            seen_abbrevs = set()
            for f in files:
                for abbr in self._extract_book_abbreviations(f[1]):
                    if abbr not in seen_abbrevs:
                        seen_abbrevs.add(abbr)
                        abbreviations.append(abbr)

            # If multiple abbreviations found, create separate books for each
            if len(abbreviations) > 1:
                for i, abbr in enumerate(abbreviations):
                    sub_book_id = abbr.lower()
                    sub_book_name = MULTI_ABBREV_NAMES.get(abbr, abbr)
                    # Assign fractional order to maintain relative ordering
                    sub_order = order + (i * 0.1)

                    book = Book(
                        id=sub_book_id,
                        name=sub_book_name,
                        abbreviations=[abbr],
                        order=sub_order,
                        testament=testament,
                        files=[f[1] for f in files]
                    )
                    self.books[sub_book_id] = book
                    self._abbrev_to_book[abbr] = sub_book_id
            else:
                book = Book(
                    id=book_id,
                    name=display_name,
                    abbreviations=abbreviations,
                    order=order,
                    testament=testament,
                    files=[f[1] for f in files]
                )
                self.books[book_id] = book
                for abbr in abbreviations:
                    self._abbrev_to_book[abbr] = book_id

    def _extract_book_abbreviations(self, filename: str) -> list[str]:
        """Extract ALL book abbreviations from verse IDs in the file.

        Some files (like Daniel.html) contain multiple texts with different
        abbreviations (Sus, Dan, Bel). We need to extract verses for all of them.
        """
        filepath = self.oebps_dir / filename
        if not filepath.exists():
            return []

        content = filepath.read_text(encoding='utf-8')
        # Find all unique abbreviations like id="Gen_vchap, id="Dan_vchap, etc.
        matches = re.findall(r'id="([A-Za-z0-9]+)_vchap', content)
        # Return unique abbreviations in order of first occurrence
        seen = set()
        abbreviations = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                abbreviations.append(m)
        return abbreviations

    def _parse_patristic_sources(self):
        """Parse Source_Abbreviations.html for patristic sources."""
        filepath = self.oebps_dir / "Source_Abbreviations.html"
        soup = BeautifulSoup(filepath.read_text(encoding='utf-8'), 'lxml')

        # Find all table rows
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                name = self._clean_text(cells[0].get_text())
                abbrev = self._clean_text(cells[1].get_text())

                if name and abbrev and name != "Source":  # Skip header
                    source = PatristicSource(id=abbrev, name=name)
                    self.patristic_sources[abbrev] = source

    def _parse_cross_references(self):
        """Parse crossReference.html for cross-reference data."""
        filepath = self.oebps_dir / "crossReference.html"
        soup = BeautifulSoup(filepath.read_text(encoding='utf-8'), 'lxml')

        # Find all fcross entries by ID pattern
        fcross_pattern = re.compile(r'^fcross\d+$')
        for div in soup.find_all('div', id=fcross_pattern):
            cross_id = div.get('id')

            # Get the full text of the cross-reference, preserving <i> and <b>
            cross_text = self._clean_text(self._extract_styled_text(div))

            # Find all target passage links (excluding the back-reference)
            targets = []
            for link in div.find_all('a'):
                href = link.get('href', '')
                # Extract passage ID from href like "Isaiah.html#Isa_vchap7-14"
                if '_vchap' in href:
                    match = re.search(r'#([A-Za-z0-9]+_vchap\d+-\d+)', href)
                    if match:
                        targets.append(match.group(1))

            self._cross_refs[cross_id] = {
                'targets': targets,
                'text': cross_text,
                'html': str(div)
            }

    def _parse_study_notes(self):
        """Parse study1-11.html files for study annotations."""
        for i in range(1, 12):
            filepath = self.oebps_dir / f"study{i}.html"
            if filepath.exists():
                self._parse_annotation_file(filepath, "study")

    def _parse_liturgical_notes(self):
        """Parse x-liturgical.html for liturgical annotations."""
        filepath = self.oebps_dir / "x-liturgical.html"
        if filepath.exists():
            self._parse_annotation_file(filepath, "liturgical")

    def _parse_variant_notes(self):
        """Parse variant.html for textual variant annotations (NU-Text/M-Text)."""
        filepath = self.oebps_dir / "variant.html"
        if filepath.exists():
            self._parse_annotation_file(filepath, "variant")

    def _parse_citation_notes(self):
        """Parse citation.html for 'see note at X' cross-references.

        These notes point readers to study notes at other passages. We extract
        the target passage ID so the reference is followable in the database.
        Preserves <i> and <b> tags in the annotation text.
        """
        filepath = self.oebps_dir / "citation.html"
        if not filepath.exists():
            return

        soup = BeautifulSoup(filepath.read_text(encoding='utf-8'), 'lxml')

        for div in soup.find_all('div', class_='footnotedef'):
            ann_id = div.get('id')
            if not ann_id:
                continue

            # Get the back-reference link to find verse display
            back_link = div.find('a')
            verse_display = ""
            if back_link:
                verse_display = self._clean_text(back_link.get_text())

            # Get full annotation text, preserving <i> and <b> tags
            ann_text = self._clean_text(self._extract_styled_text(div))
            ann_html = str(div)

            # Extract target passage IDs from links within the note
            # These are the "See note at X:Y" targets
            target_refs = []
            for link in div.find_all('a'):
                href = link.get('href', '')
                # Look for passage links like "Exodus.html#Exod_vchap4-21"
                match = re.search(r'#([A-Za-z0-9]+_vchap\d+-\d+)', href)
                if match:
                    target_refs.append(match.group(1))

            annotation = Annotation(
                id=ann_id,
                type="citation",
                passage_ids=[],  # Will be populated when parsing passages
                verse_display=verse_display,
                text=ann_text,
                html=ann_html,
                patristic_citations=[],
                scripture_refs=target_refs  # The "see note at X" targets
            )

            self.annotations[ann_id] = annotation

    def _parse_annotation_file(self, filepath: Path, ann_type: str):
        """Parse an annotation file (study or liturgical), preserving <i> and <b> tags."""
        soup = BeautifulSoup(filepath.read_text(encoding='utf-8'), 'lxml')

        for div in soup.find_all('div', class_=['footnotedef', 'footnotepara']):
            ann_id = div.get('id')
            if not ann_id:
                continue

            # Get the back-reference link to find verse display
            back_link = div.find('a')
            verse_display = ""
            passage_ids = []

            if back_link:
                # Extract verse display from link text (e.g., "1:1" or "1:1-3")
                # No styling needed here - just the verse reference
                verse_display = self._clean_text(back_link.get_text())

                # Extract passage ID from href
                href = back_link.get('href', '')
                if '#fn' in href or '#fnx' in href:
                    # This links back to the marker in the text
                    # We'll resolve passage IDs when parsing passages
                    pass

            # Get full annotation text, preserving <i> and <b> tags
            ann_text = self._clean_text(self._extract_styled_text(div))
            ann_html = str(div)

            # Extract patristic citations (patterns like (BasilG) or (JohnChr))
            # Use plain text for pattern matching
            plain_text = div.get_text()
            patristic = self._extract_patristic_citations(plain_text)

            # Extract scripture references within the annotation
            scripture_refs = self._extract_scripture_refs(div)

            annotation = Annotation(
                id=ann_id,
                type=ann_type,
                passage_ids=passage_ids,  # Will be populated when parsing passages
                verse_display=verse_display,
                text=ann_text,
                html=ann_html,
                patristic_citations=patristic,
                scripture_refs=scripture_refs
            )

            self.annotations[ann_id] = annotation

    def _extract_patristic_citations(self, text: str) -> list[str]:
        """Extract patristic source citations from text."""
        citations = []
        # Simple pattern: find anything in parentheses
        for match in re.finditer(r'\(([^)]+)\)', text):
            inner = match.group(1)
            # Split on comma, semicolon, or whitespace and check each part
            for part in re.split(r'[,;\s]+', inner):
                part = part.strip()
                # Skip common filler words
                if part.lower() in ('and', 'or', 'cf', 'cf.', 'see', 'also'):
                    continue
                if part in self.patristic_sources:
                    citations.append(part)
        return list(set(citations))

    def _extract_scripture_refs(self, element) -> list[str]:
        """Extract scripture passage references from annotation element."""
        refs = []
        for link in element.find_all('a'):
            href = link.get('href', '')
            if '_vchap' in href:
                match = re.search(r'#?([A-Za-z0-9]+_vchap\d+-\d+)', href)
                if match:
                    refs.append(match.group(1))
        return refs

    def _parse_passages(self):
        """Parse all biblical book files to extract passages."""
        for book_id, book in self.books.items():
            for filename in book.files:
                self._parse_book_file(book, filename)

    def _parse_book_file(self, book: Book, filename: str):
        """Parse a single book HTML file."""
        filepath = self.oebps_dir / filename
        if not filepath.exists():
            print(f"  Warning: {filename} not found")
            return

        content = filepath.read_text(encoding='utf-8')
        soup = BeautifulSoup(content, 'lxml')

        # Extract inline topical articles BEFORE stripping/modifying the soup
        # This creates article annotations and returns verse_id -> [article_ids] mapping
        verse_to_articles = self._extract_articles(soup, book)

        # Pre-collect variant IDs before stripping (since stripping removes them)
        variant_markers = self._collect_variant_markers(soup)

        # Pre-collect ALL annotation markers with preceding context before stripping
        # This captures position data for study, liturgical, variant, citation, and cross-ref markers
        annotation_markers = self._collect_annotation_markers(soup)

        # Strip variant markers before extraction (removes <sup><a href="variant.html">a</a></sup>)
        self._strip_variant_markers(soup)

        # Build pattern to match ANY of the book's abbreviations
        # e.g., for Daniel: (Sus|Dan|Bel)_vchap(\d+)-(\d+)
        abbrev_pattern = '|'.join(re.escape(a) for a in book.abbreviations)
        verse_pattern = re.compile(rf'^({abbrev_pattern})_vchap(\d+)-(\d+)$')

        # Process elements with verse IDs
        for element in soup.find_all(id=verse_pattern):
            verse_id = element.get('id')
            match = verse_pattern.match(verse_id)
            if not match:
                continue

            abbrev = match.group(1)  # The abbreviation that matched
            chapter = int(match.group(2))
            verse = int(match.group(3))

            # Look up the correct book_id for this abbreviation
            # (important for multi-text files like Daniel.html -> sus, dan, bel)
            actual_book_id = self._abbrev_to_book.get(abbrev, book.id)

            # Determine format and extraction method based on element context
            parent_ol = element.find_parent('ol')
            if element.name == 'ol':
                # Verse marker IS the ol element
                fmt = "poetry"
                verse_html, verse_text = self._extract_poetry_verse(element, verse_id, abbrev)
            elif parent_ol:
                # Verse marker is inside an ol (e.g., <sup> in <li> in <ol>)
                # Extract from the ol, not from a distant parent div
                fmt = "poetry"
                verse_html, verse_text = self._extract_poetry_verse_from_marker(
                    element, parent_ol, verse_id, abbrev
                )
            else:
                fmt = "prose"
                verse_html, verse_text = self._extract_prose_verse(element, soup, verse_id, abbrev)

            # Extract annotation references
            study_ids, liturgical_ids, _, citation_ids, cross_ref_data = self._extract_annotation_refs(
                element, soup, verse_id, filename
            )

            # Use pre-collected variant IDs (since variant markers are stripped before extraction)
            verse_variant_ids = variant_markers.get(verse_id, [])

            # Get pre-collected annotation markers with position data
            verse_markers = annotation_markers.get(verse_id, [])

            # Extract cross-ref data from pre-collected markers (fixes cross-ref linkage bug)
            # Cross-ref markers are stripped before _extract_annotation_refs runs, so we use
            # the pre-collected data instead
            cross_ref_targets = []
            cross_ref_text = None
            for marker in verse_markers:
                if marker.type == 'cross_ref' and marker.id in self._cross_refs:
                    cr = self._cross_refs[marker.id]
                    if cr['targets'] and not cross_ref_targets:  # Take first cross-ref for backwards compat
                        cross_ref_targets = cr['targets']
                        cross_ref_text = cr['text']

            # Get article IDs linked to this verse
            verse_article_ids = verse_to_articles.get(verse_id, [])

            passage = Passage(
                id=verse_id,
                book_id=actual_book_id,
                chapter=chapter,
                verse=verse,
                text=verse_text,
                html=verse_html,
                format=fmt,
                study_note_ids=study_ids,
                liturgical_ids=liturgical_ids,
                variant_ids=verse_variant_ids,
                citation_ids=citation_ids,
                article_ids=verse_article_ids,
                cross_ref_targets=cross_ref_targets,
                cross_ref_text=cross_ref_text,
                annotation_markers=verse_markers
            )

            self.passages[verse_id] = passage

            # Update annotation passage_ids (articles already have passage_ids set during extraction)
            for ann_id in study_ids + liturgical_ids + verse_variant_ids + citation_ids:
                if ann_id in self.annotations:
                    if verse_id not in self.annotations[ann_id].passage_ids:
                        self.annotations[ann_id].passage_ids.append(verse_id)

    def _extract_prose_verse(self, element, soup, verse_id: str, book_abbrev: str) -> tuple[str, str]:
        """Extract text for a prose verse, preserving <i> and <b> tags.

        For prose, verse content follows the verse marker until:
        - Next verse marker
        - Structural boundary (psalm header, section header)
        - End of scannable content

        This also follows sibling elements to capture content that spans
        multiple elements (e.g., psalm titles in <p> followed by content in <ol>).
        """
        # Find the parent paragraph
        parent = element.find_parent(['p', 'div'])
        if not parent:
            return str(element), self._clean_text(self._extract_styled_text(element))

        verse_text_parts = []
        next_verse_pattern = re.compile(rf'^{re.escape(book_abbrev)}_vchap\d+-\d+$')

        def extract_styled_until_boundary(elem, start_after_id=None):
            """Extract styled text from element, optionally starting after a specific ID.

            Returns (list of HTML fragments, hit_boundary).
            """
            parts = []
            collecting = start_after_id is None
            # Track open tags for proper nesting
            in_italic = False
            in_bold = False

            for descendant in elem.descendants:
                # Start collecting after we pass the verse marker
                if not collecting:
                    if hasattr(descendant, 'get') and descendant.get('id') == start_after_id:
                        collecting = True
                    continue

                # Stop at next verse marker
                if hasattr(descendant, 'get'):
                    desc_id = descendant.get('id', '')
                    if desc_id and next_verse_pattern.match(desc_id) and desc_id != verse_id:
                        return parts, True  # hit_boundary = True

                # Track entry/exit of <i> and <b> tags
                if hasattr(descendant, 'name'):
                    if descendant.name == 'i':
                        in_italic = True
                    elif descendant.name == 'b':
                        in_bold = True

                if isinstance(descendant, NavigableString):
                    text = str(descendant)
                    if text.strip():
                        # Wrap in appropriate tags based on current context
                        # Check parent chain for <i> and <b>
                        parent_i = descendant.find_parent('i')
                        parent_b = descendant.find_parent('b')
                        if parent_i and parent_b:
                            parts.append(f'<b><i>{text}</i></b>')
                        elif parent_i:
                            parts.append(f'<i>{text}</i>')
                        elif parent_b:
                            parts.append(f'<b>{text}</b>')
                        else:
                            parts.append(text)

            return parts, False

        # Extract from parent paragraph, starting after our verse marker
        parts, hit_boundary = extract_styled_until_boundary(parent, start_after_id=verse_id)
        verse_text_parts.extend(parts)

        # If we didn't hit a verse boundary, scan following siblings
        if not hit_boundary:
            sibling = parent.find_next_sibling()
            while sibling:
                # Stop at structural boundaries (psalm headers, section headers)
                if self._is_boundary(sibling):
                    break

                # Only scan content elements
                if hasattr(sibling, 'name') and sibling.name in ['ol', 'p', 'div']:
                    parts, hit_boundary = extract_styled_until_boundary(sibling)
                    verse_text_parts.extend(parts)
                    if hit_boundary:
                        break

                sibling = sibling.find_next_sibling()

        verse_text = self._clean_text(' '.join(verse_text_parts))
        verse_html = str(element)

        return verse_html, verse_text

    def _extract_poetry_verse(self, element, verse_id: str, book_abbrev: str) -> tuple[str, str]:
        """Extract text for a poetry verse (ol/li structure), preserving <i> and <b> tags."""
        # For poetry, the ol element contains li elements for each line
        lines = []

        # Get all li elements until the next verse marker
        next_verse_pattern = re.compile(rf'^{re.escape(book_abbrev)}_vchap\d+-\d+$')

        for li in element.find_all('li'):
            # Check if this li contains a different verse marker
            has_other_verse = False
            for child in li.find_all(id=next_verse_pattern):
                if child.get('id') != verse_id:
                    has_other_verse = True
                    break

            if has_other_verse:
                break

            line_text = self._clean_text(self._extract_styled_text(li))
            if line_text:
                lines.append(line_text)

        verse_text = '\n'.join(lines)
        verse_html = str(element)

        return verse_html, verse_text

    def _extract_poetry_verse_from_marker(
        self, marker_element, parent_ol, verse_id: str, book_abbrev: str
    ) -> tuple[str, str]:
        """Extract text for a poetry verse when marker is inside the ol (e.g., <sup> in <li>).

        This handles the common case where verse markers are <sup> elements inside
        <li> elements, rather than on the <ol> itself. We scan from the marker
        to the next verse marker, staying within the parent ol bounds.
        Preserves <i> and <b> tags.
        """
        parts = []
        next_verse_pattern = re.compile(rf'^{re.escape(book_abbrev)}_vchap\d+-\d+$')

        # Track if we've passed the current verse marker
        found_marker = False

        for descendant in parent_ol.descendants:
            # Find our verse marker to start collecting
            if not found_marker:
                if hasattr(descendant, 'get') and descendant.get('id') == verse_id:
                    found_marker = True
                continue

            # Stop at next verse marker
            if hasattr(descendant, 'get'):
                desc_id = descendant.get('id', '')
                if desc_id and next_verse_pattern.match(desc_id) and desc_id != verse_id:
                    break

            # Collect text from NavigableStrings, preserving <i> and <b> context
            if isinstance(descendant, NavigableString):
                text = str(descendant).strip()
                if text:
                    # Check parent chain for <i> and <b>
                    parent_i = descendant.find_parent('i')
                    parent_b = descendant.find_parent('b')
                    if parent_i and parent_b:
                        parts.append(f'<b><i>{text}</i></b>')
                    elif parent_i:
                        parts.append(f'<i>{text}</i>')
                    elif parent_b:
                        parts.append(f'<b>{text}</b>')
                    else:
                        parts.append(text)

        verse_text = self._clean_text(' '.join(parts))
        verse_html = str(marker_element)

        return verse_html, verse_text

    def _extract_annotation_refs(self, element, soup, verse_id: str, filename: str) -> tuple[list, list, list, list, dict]:
        """Extract study note, liturgical, variant, citation, and cross-ref IDs for a verse."""
        study_ids = []
        liturgical_ids = []
        variant_ids = []
        citation_ids = []
        cross_ref_data = {'targets': [], 'text': None}

        # Extract book abbreviation from verse_id for boundary detection
        # e.g., "Gen_vchap1-1" -> "Gen"
        book_abbrev = verse_id.split('_')[0] if '_' in verse_id else ""
        next_verse_pattern = re.compile(rf'^{re.escape(book_abbrev)}_vchap\d+-\d+$') if book_abbrev else None

        def extract_from_element(elem, stop_at_next_verse=False):
            """Extract annotation IDs from an element, optionally stopping at next verse.

            Uses document order traversal to handle cases where annotations and
            the next verse marker are in the same element (e.g., poetry <ol>).
            """
            s_ids, l_ids, v_ids, c_ids = [], [], [], []
            cr_data = {'targets': [], 'text': None}
            hit_boundary = False

            # Iterate through all descendants in document order
            for descendant in elem.descendants:
                # Check for verse boundary marker
                if stop_at_next_verse and next_verse_pattern:
                    if hasattr(descendant, 'get') and descendant.get('id'):
                        desc_id = descendant.get('id')
                        if next_verse_pattern.match(desc_id) and desc_id != verse_id:
                            # Hit the next verse - stop extracting
                            hit_boundary = True
                            break

                # Extract annotation links
                if hasattr(descendant, 'name') and descendant.name == 'a':
                    href = descendant.get('href', '')

                    # Study note reference
                    if 'study' in href and '#f' in href:
                        match = re.search(r'#(f\d+)', href)
                        if match:
                            s_ids.append(match.group(1))

                    # Liturgical reference
                    elif 'liturgical' in href and '#fx' in href:
                        match = re.search(r'#(fx\d+)', href)
                        if match:
                            l_ids.append(match.group(1))

                    # Variant note reference
                    elif 'variant.html' in href and '#fvar' in href:
                        match = re.search(r'#(fvar\d+)', href)
                        if match:
                            v_ids.append(match.group(1))

                    # Citation note reference
                    elif 'citation.html' in href and '#fcit' in href:
                        match = re.search(r'#(fcit\d+)', href)
                        if match:
                            c_ids.append(match.group(1))

                    # Cross-reference
                    elif 'crossReference' in href and '#fcross' in href:
                        match = re.search(r'#(fcross\d+)', href)
                        if match:
                            cross_id = match.group(1)
                            if cross_id in self._cross_refs:
                                cr = self._cross_refs[cross_id]
                                cr_data['targets'] = cr['targets']
                                cr_data['text'] = cr['text']

            return s_ids, l_ids, v_ids, c_ids, cr_data, hit_boundary

        if element.name == 'ol':
            # Poetry: the verse marker IS the ol element, scan it
            s, l, v, c, cr, _ = extract_from_element(element)
            study_ids.extend(s)
            liturgical_ids.extend(l)
            variant_ids.extend(v)
            citation_ids.extend(c)
            if cr['targets']:
                cross_ref_data = cr
        elif element.find_parent('ol'):
            # Poetry context: verse marker is inside an ol (e.g., <sup> in <li> in <ol>)
            # Need to scan from AFTER the current verse marker to the next verse marker
            parent_ol = element.find_parent('ol')

            # Custom extraction that skips until we're past the current verse marker
            found_current_verse = False
            for descendant in parent_ol.descendants:
                # First, find the current verse marker
                if not found_current_verse:
                    if hasattr(descendant, 'get') and descendant.get('id') == verse_id:
                        found_current_verse = True
                    continue

                # Check for next verse boundary
                if next_verse_pattern:
                    if hasattr(descendant, 'get') and descendant.get('id'):
                        desc_id = descendant.get('id')
                        if next_verse_pattern.match(desc_id) and desc_id != verse_id:
                            break  # Hit next verse, stop

                # Extract annotation links
                if hasattr(descendant, 'name') and descendant.name == 'a':
                    href = descendant.get('href', '')
                    if 'study' in href and '#f' in href:
                        match = re.search(r'#(f\d+)', href)
                        if match:
                            study_ids.append(match.group(1))
                    elif 'liturgical' in href and '#fx' in href:
                        match = re.search(r'#(fx\d+)', href)
                        if match:
                            liturgical_ids.append(match.group(1))
                    elif 'variant.html' in href and '#fvar' in href:
                        match = re.search(r'#(fvar\d+)', href)
                        if match:
                            variant_ids.append(match.group(1))
                    elif 'citation.html' in href and '#fcit' in href:
                        match = re.search(r'#(fcit\d+)', href)
                        if match:
                            citation_ids.append(match.group(1))
                    elif 'crossReference' in href and '#fcross' in href:
                        match = re.search(r'#(fcross\d+)', href)
                        if match:
                            cross_id = match.group(1)
                            if cross_id in self._cross_refs and not cross_ref_data['targets']:
                                cr = self._cross_refs[cross_id]
                                cross_ref_data['targets'] = cr['targets']
                                cross_ref_data['text'] = cr['text']
        else:
            # Prose: look in parent paragraph AND following siblings until next verse
            parent_p = element.find_parent('p')
            if parent_p:
                # First, extract from the parent paragraph
                s, l, v, c, cr, _ = extract_from_element(parent_p)
                study_ids.extend(s)
                liturgical_ids.extend(l)
                variant_ids.extend(v)
                citation_ids.extend(c)
                if cr['targets']:
                    cross_ref_data = cr

                # Then scan following siblings until we hit the next verse marker or boundary
                sibling = parent_p.find_next_sibling()
                while sibling:
                    # Stop at structural boundaries (psalm headers, section headers)
                    if self._is_boundary(sibling):
                        break

                    # Only scan ol, p, div elements (skip text nodes, etc.)
                    if hasattr(sibling, 'name') and sibling.name in ['ol', 'p', 'div']:
                        s, l, v, c, cr, hit_boundary = extract_from_element(sibling, stop_at_next_verse=True)
                        # Always save extracted IDs (even if we hit boundary, we got
                        # annotations that appeared before the boundary marker)
                        study_ids.extend(s)
                        liturgical_ids.extend(l)
                        variant_ids.extend(v)
                        citation_ids.extend(c)
                        if cr['targets'] and not cross_ref_data['targets']:
                            cross_ref_data = cr
                        # Now check if we hit boundary and should stop scanning
                        if hit_boundary:
                            break
                        # If this sibling is a paragraph with verse markers, stop
                        if sibling.name == 'p' and sibling.find(id=next_verse_pattern):
                            break
                    sibling = sibling.find_next_sibling()

        return study_ids, liturgical_ids, variant_ids, citation_ids, cross_ref_data

    def _extract_styled_text(self, element) -> str:
        """Extract text from element, preserving <i> and <b> tags.

        This creates a deep copy of the element, then unwraps all tags except
        <i> and <b>, preserving their semantic meaning in the output.
        """
        if element is None:
            return ""

        # Make a deep copy so we don't modify the original
        elem_copy = copy.copy(element)
        # Need to use BeautifulSoup to parse the string representation
        # to get a fully independent copy
        elem_soup = BeautifulSoup(str(element), 'lxml')
        elem_copy = elem_soup.body if elem_soup.body else elem_soup

        # Tags to preserve (will not be unwrapped)
        preserve_tags = {'i', 'b'}

        # Find all tags and unwrap those not in preserve_tags
        # We need to iterate carefully since we're modifying the tree
        # Process from deepest to shallowest to avoid issues
        all_tags = list(elem_copy.find_all(True))  # True matches all tags
        for tag in reversed(all_tags):
            if tag.name not in preserve_tags:
                tag.unwrap()

        # Get the inner HTML (which now only contains text and <i>/<b> tags)
        result = ''.join(str(child) for child in elem_copy.children)

        return result

    def _clean_text(self, text: str) -> str:
        """Clean extracted text, preserving <i> and <b> tags."""
        if not text:
            return ""
        # Remove annotation markers (dagger for study, omega for liturgical)
        text = re.sub(r'[†‡ω]', '', text)
        # Normalize whitespace (but not inside tags)
        # First, protect content inside tags by replacing internal spaces
        # Actually, just normalize all whitespace - tags are inline
        text = re.sub(r'\s+', ' ', text)
        # Fix drop-cap spacing: "T he" -> "The"
        # Only at start of text or after sentence-ending punctuation
        # (drop-caps only appear at the beginning of verses/sections)
        text = re.sub(r'^([A-Z]) ([a-z])', r'\1\2', text)  # Start of text
        text = re.sub(r'(\. )([A-Z]) ([a-z])', r'\1\2\3', text)  # After period
        # Remove leading/trailing whitespace
        text = text.strip()
        # Remove verse numbers that might have been included
        # (they appear as standalone numbers at start)
        text = re.sub(r'^\d+\s+', '', text)
        # Clean up any empty tags that might result from stripping
        text = re.sub(r'<([ib])>\s*</\1>', '', text)
        # Normalize spaces around tags
        text = re.sub(r'\s+<', ' <', text)
        text = re.sub(r'>\s+', '> ', text)
        # Fix spaces inside tags at boundaries: "< i>" -> "<i>", "</i >" -> "</i>"
        text = re.sub(r'<\s+', '<', text)
        text = re.sub(r'\s+>', '>', text)
        return text.strip()
