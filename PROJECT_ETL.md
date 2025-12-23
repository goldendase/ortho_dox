# Orthodox Study Bible Extraction Pipeline

## Overview

This project extracts content from the Orthodox Study Bible (OSB) EPUB and loads it into MongoDB for use in a theological study pipeline. The extraction preserves:

- All 78 canonical books (the full Orthodox Old Testament + New Testament)

**Note on Canon**: The Orthodox Church recognizes all 78 books as canonical Scripture. There is no "Deuterocanonical" distinction - that's a Western (Catholic/Protestant) framework. Books like Tobit, Wisdom of Solomon, Sirach, etc. are simply part of the Old Testament, as received from the Septuagint tradition. Do not use Protestant terminology or framing when working with this codebase.
- Verse text with book/chapter/verse structure (with semantic `<i>` and `<b>` markup preserved)
- Study notes with patristic citations
- Liturgical notes
- Textual variant notes (NU-Text/M-Text manuscript differences)
- Citation cross-references ("See note at X")
- Cross-references between passages
- Raw HTML for future re-processing

## Project Structure

```
orthodox/
├── ortbible.epub           # Source EPUB file
├── epub_extracted/         # Extracted EPUB contents
│   └── OEBPS/              # Main content directory
│       ├── content.opf     # Manifest with book metadata
│       ├── toc.ncx         # Table of contents
│       ├── *.html          # Book content files
│       ├── study1-11.html  # Study note files
│       ├── x-liturgical.html
│       ├── variant.html    # NT textual variants (932 notes)
│       ├── citation.html   # "See note at X" references (229 notes)
│       ├── crossReference.html
│       └── Source_Abbreviations.html
├── extract.py              # Main extraction script
├── parser/
│   ├── __init__.py
│   ├── models.py           # Data models (Book, Passage, Annotation, PatristicSource)
│   ├── epub_parser.py      # OSBParser - main parsing logic
│   └── mongo_loader.py     # MongoLoader - database loading
├── requirements.txt
└── PROJECT_ETL.md          # This file
```

### Unparsed EPUB Files

The following EPUB files exist but are intentionally not parsed (minimal content, not worth the complexity):

| File | Entries | Content | Reason Skipped |
|------|---------|---------|----------------|
| `alternative.html` | 5 | Alternative readings ("Or *spirit*") | Too few to matter |
| `translation.html` | 4 | Greek/Aramaic terms ("Greek *anathema*") | Too few to matter |
| `background.html` | 2 | Historical notes ("Patmos: A small rocky island...") | Only 2 entries total |

## Data Schemas

### MongoDB Databases

Two databases are created:
- `ortho_dox` - Clean extracted text
- `ortho_raw` - Raw HTML preserved

### Collections

#### `ortho_dox.books`
```javascript
{
  _id: "genesis",           // Lowercase book name, no spaces
  name: "Genesis",          // Display name
  abbreviation: "Gen",      // From verse IDs (e.g., Gen_vchap1-1)
  order: 1,                 // Canonical order from manifest
  testament: "old",         // "old" or "new"
  files: ["Genesis.html", "Genesis1.html"]  // Source HTML files
}
```

#### `ortho_dox.passages`
```javascript
{
  _id: "Gen_vchap1-1",      // Verbatim from EPUB (DO NOT PARSE)
  book_id: "genesis",
  chapter: 1,
  verse: 1,
  text: "In the beginning God made heaven and earth.",
  format: "prose",          // "prose" or "poetry"
  study_note_ids: ["f1", "f2", "f3", "f4"],
  liturgical_ids: ["fx1"],
  variant_ids: ["fvar1"],   // NT textual variant notes
  citation_ids: ["fcit1"],  // "See note at X" references
  article_ids: ["creation"], // Topical study articles
  cross_ref_targets: ["Isa_vchap7-14"],  // Target passage IDs
  cross_ref_text: "1:23a Isaiah 7:14...",  // Full cross-ref text
  annotation_markers: [     // Position data for markers in THIS verse
    { id: "f1", type: "study", preceding: "made heaven and earth." },
    { id: "fx1", type: "liturgical", preceding: "made heaven and earth." }
  ]
}
```

**Note on annotation_markers vs *_ids fields:**
- `study_note_ids`, `liturgical_ids`, etc. list annotations that **cover** this verse (an annotation may cover multiple verses)
- `annotation_markers` shows which markers **physically appear** in this verse's text, with ~40 chars of preceding context for precise location

#### `ortho_dox.annotations`
```javascript
{
  _id: "f1",                // Annotation ID (f*, fx*, fvar*, fcit*, or article slug)
  type: "study",            // "study", "liturgical", "variant", "citation", or "article"
  passage_ids: ["Gen_vchap1-1"],  // Linked passages
  verse_display: "1:1",     // Human-readable reference
  text: "1:1 God the Father made heaven and earth...",
  patristic_citations: ["BasilG", "JohnChr"],  // Source abbreviations (study notes only)
  scripture_refs: ["Ps_vchap25-12"]  // Scripture references within note
}
```

**Annotation Types:**

| Type | ID Pattern | Count | Description |
|------|------------|-------|-------------|
| `study` | `f{n}` | 6,290 | Patristic commentary and theological notes |
| `liturgical` | `fx{n}` | 365 | Liturgical usage references |
| `variant` | `fvar{n}` | 932 | NT manuscript variants (NU-Text vs M-Text) |
| `citation` | `fcit{n}` | 229 | "See note at X" cross-references |
| `article` | slug | 47 | Topical study articles (e.g., "creation", "trinity") |

**Citation Notes** are followable references. The `scripture_refs` field contains the target passage ID(s):
```javascript
// Citation note saying "See note at 4:21"
{
  _id: "fcit1",
  type: "citation",
  passage_ids: ["Exod_vchap7-3"],  // Where the marker appears
  text: "7:3 See note at 4:21.",
  scripture_refs: ["Exod_vchap4-21"]  // The target - followable in DB
}
```

**Article Annotations** are topical study essays embedded inline in the biblical text:
```javascript
// Article on "CREATION" linked to Genesis 1:1
{
  _id: "creation",               // Slug from HTML id attribute
  type: "article",
  passage_ids: ["Gen_vchap1-1"], // Following verse (article appears before this verse)
  verse_display: "1:1",
  text: "CREATION\n\n\"We believe in one God, the Father Almighty...",
  scripture_refs: ["Gen_vchap1-2", "Ps_vchap103-30", "Gen_vchap1-26"]  // Scripture citations within
}
```

#### `ortho_dox.patristic_sources`
```javascript
{
  _id: "BasilG",            // Abbreviation used in citations
  name: "Basil the Great"   // Full name
}
```

#### `ortho_raw.passages` / `ortho_raw.annotations`
Same structure but with `html` field instead of `text`.

## EPUB Structure - Important Patterns

### Verse ID Format
```
{BookAbbr}_vchap{Chapter}-{Verse}
```
Examples: `Gen_vchap1-1`, `Ps_vchap23-1`, `Matt_vchap5-12`

**CRITICAL**: Use these IDs as opaque keys. Do NOT regex-parse them to derive chapter/verse - the structure comes from HTML hierarchy.

**Note on Psalm Numbering**: The OSB uses Septuagint (LXX) numbering. What Protestants call "Psalm 23" (The Lord is my shepherd) is `Ps_vchap22-1` in this database. Most Psalms are numbered one lower than in Protestant/Masoretic Bibles.

### Book HTML Structure

**Prose books** (Genesis, Matthew, etc.):
```html
<p class="chapter1">
  <span class="chbeg" id="Gen_vchap1-1">1</span>
  In the beginning God made heaven and earth.
  <sup><a href="study1.html#f1" id="fn1">†</a></sup>
  <sup id="Gen_vchap1-2">2</sup>
  The earth was invisible...
</p>
```

**Poetry books** (Psalms, Proverbs, etc.):
```html
<p class="psalm2">
  <sup id="Ps_vchap4-1">1</sup>
  <i>For the End; in psalms...</i>
  <sup><a href="study3.html#f2000" id="fn2000">†</a></sup>
</p>
<ol class="olstyle" id="Ps_vchap4-2">
  <li>You heard me when I called...</li>
  <li><sup id="Ps_vchap4-3">3</sup> How long, O you sons...</li>
</ol>
```

### Annotation Markers
- Study notes: `<sup><a href="study1.html#f1" id="fn1">†</a></sup>`
- Liturgical: `<sup><a href="x-liturgical.html#fx1" id="fnx1">ω</a></sup>`
- Variants: `<sup><a href="variant.html#fvar1" id="fvarx1">a</a></sup>`
- Citations: `<sup><a href="citation.html#fcit1" id="fcitx1">a</a></sup>`
- Cross-refs: `<a href="crossReference.html#fcross1">`

### Patristic Citations
Inline in annotation text: `(JohnChr, AmbM, Eust, CyrAl, Aug, and Cass)`

## Known Issues & Gotchas

### 1. Daniel / Susanna / Bel Multi-Text Book (FIXED)
Daniel.html contains three distinct texts with different verse ID prefixes:
- `Sus_vchap*` - Susanna (64 verses)
- `Dan_vchap*` - Main Daniel content (424 verses)
- `Bel_vchap*` - Bel and the Dragon (42 verses)

The parser extracts ALL unique abbreviations from each book file and stores them as a list (`abbreviations: ["Sus", "Dan", "Bel"]`). All passages are extracted regardless of prefix.

### 2. Annotation Context Boundaries (FIXED)
Annotation markers may appear in sibling elements, not within the same parent as the verse marker. The parser now handles this by:
1. For prose verses: scanning following sibling elements (`<ol>`, `<p>`, `<div>`) until the next verse marker
2. For poetry verses: using document-order traversal from the verse marker to the next verse marker
3. For verse markers inside `<ol>` elements: scanning from the marker position to the next verse

### 3. Orphan Annotations (15 total)
Some annotations don't map to standard verse IDs. These fall into categories:

| Category | Count | Examples |
|----------|-------|----------|
| Esther Greek additions | 10 | `f1704` (1:1m-1r), `f1724` (4:17a-17x) |
| Poetry annotation distance | 3 | Song of Songs 1:4, 7:1, 8:5 |
| Hosea | 1 | `f3074` (4:1) |
| Prologue | 1 | `f6257` (Sirach Prologue) |

**Esther Greek additions** use letter-subscript verse IDs (e.g., "4:17a-17x") for content only in the LXX, not the Hebrew. The parser doesn't handle this non-standard format.

**Poetry annotation distance** occurs when the annotation marker (†) appears many lines after the verse marker in multi-line poetic stanzas.

### 4. Mixed Prose/Poetry Sections
Some books mix formats. A chapter might start with prose (`<p>`) then switch to poetry (`<ol>`). The `format` field indicates the element type of the verse marker, not the literary genre.

### 5. Multi-file Books
Large books span multiple HTML files (e.g., `Genesis.html`, `Genesis1.html`). The parser handles this via the `files` array on books.

### 6. Special Characters
- `†` (dagger) = study note marker
- `ω` (omega) = liturgical note marker
- `‡` (double dagger) = sometimes used
- These are stripped from clean text but present in raw HTML.

### 7. TOC Files (FIXED)
The manifest includes TOC files (`Psalms_toc.html`, `Acts_toc.html`) that are now filtered out during parsing - they're navigation, not content. The parser skips any file with `_toc` in the name.

### 8. Very Short Verses
Some verses are legitimately very short (e.g., "and," in Luke 4:11) due to how the OSB divides verses. These are not extraction errors.

### 9. Article/Header Content (FIXED)
The OSB includes topical articles inline with verse content. These are now properly extracted as separate `type: "article"` annotations before verse parsing occurs. Articles wrapped in `<div style="background-color: gray;">` are detected and extracted with their full content, then linked to the following verse via `article_ids`. No article headers leak into verse text.

### 10. Semantic Styling Preserved
The extracted `text` field preserves `<i>` (italic) and `<b>` (bold) tags because they carry semantic meaning in biblical publishing:

| Tag | Usage | Example |
|-----|-------|---------|
| `<i>` | OT quotations in NT | `<i>"Behold, the virgin shall be with child..."</i>` |
| `<i>` | Psalm superscriptions | `<i>A psalm by David, when he fled from Absalom.</i>` |
| `<i>` | Translator additions | `Blessed <i>are</i> the poor` (Greek has no "are") |
| `<i>` | Theological terms | `<i>Unbegotten</i>`, `<i>proceeds</i>` |
| `<i>` | Variant readings | `NU-Text omits <i>without a cause.</i>` |
| `<b>` | Scripture quotations in notes | `He uses the pronouns <b>Us</b> and <b>Our</b>` |
| `<b>` | Verse references in notes | `<b>1:26-30</b> The Holy Trinity...` |

This is intentional - the raw HTML is still available in `ortho_raw` if you need the complete markup, but `ortho_dox.text` preserves only the semantically meaningful styling.

### 11. NT Textual Variant Markers (FIXED)
The NT books contain textual variant markers indicating NU-Text/M-Text manuscript variants. These appear in several forms:
- `<sup><a href="variant.html#fvarN">a</a></sup>` - variant notes (now parsed as annotations)
- `<sup><a href="crossReference.html#fcrossN">a</a></sup>` - single-letter cross-refs (stripped)
- `<sup><a href="translation.html#ftranN">a</a></sup>` - translation notes (stripped)
- `<sup><a href="background.html#fbackN">b</a></sup>` - background notes (stripped)

Single-letter markers (a, b, c) are stripped from verse text. Variant notes are preserved as annotations with `type: "variant"`.

### 12. Structural Boundary Elements (FIXED)
Section headers (`<p class="sub1">`) and psalm chapter headers (`<p class="psalm">`) were being absorbed into the preceding verse text. The parser now recognizes these CSS classes as boundaries that stop text scanning:
- `psalm` - Psalm chapter headers (e.g., "Psalm 16 (17)")
- `sub1` - Section headers (e.g., "The Garden of Eden")
- `sub2` - Sub-section headers

### 13. Poetry Verse Markers Inside `<ol>` (FIXED)
Most poetry verses (Psalms, Proverbs, etc.) have verse markers as `<sup>` elements inside `<li>` inside `<ol>`, not on the `<ol>` itself. The parser now detects this context and uses appropriate extraction that stays within the `<ol>` bounds rather than scanning distant parent elements.

### 14. Drop-Cap Letter Spacing (FIXED)
Some verses begin with drop-cap styling where the first letter is in a separate `<span class="chbeg">` element (e.g., `<span class="chbeg">T</span>he Lord`). This was causing spacing artifacts ("T he Lord"). The parser now joins single capital letters with following lowercase text at verse starts.

### 15. Inline Topical Articles (EXTRACTED)
The OSB includes 47 topical study articles (e.g., "THE SABBATH DAY", "MARRIAGE", "THE CHURCH") embedded inline between verses. These are wrapped in `<div style="background-color: gray;">` and contain:
- `<p class="ct" id="slug">` - Centered title with spaced letters (T H E  C H U R C H)
- `<p class="sub1">` - Section headers
- `<p class="tx1">` / `<p class="tx">` - Article body text

The parser extracts these as `type: "article"` annotations with:
- ID from the `<p class="ct">` element's `id` attribute (e.g., "creation", "trinity")
- Cleaned title (spaced letters collapsed, `<br/>` converted to spaces)
- Full article text with section structure preserved
- Scripture references extracted from internal links
- Linked to the **following** verse via `article_ids` on the passage

## Indexes Created

```javascript
// Passages
db.passages.createIndex("book_id")
db.passages.createIndex({book_id: 1, chapter: 1})
db.passages.createIndex({book_id: 1, chapter: 1, verse: 1})
db.passages.createIndex("cross_ref_targets")
db.passages.createIndex("study_note_ids")
db.passages.createIndex("liturgical_ids")
db.passages.createIndex("variant_ids")
db.passages.createIndex("citation_ids")
db.passages.createIndex("article_ids")

// Annotations
db.annotations.createIndex("type")
db.annotations.createIndex("passage_ids")
db.annotations.createIndex("patristic_citations")

// Raw passages
db.passages.createIndex("book_id")
db.passages.createIndex({book_id: 1, chapter: 1})
```

## Usage

```bash
# Extract EPUB (first time only)
unzip ortbible.epub -d epub_extracted

# Run extraction
python extract.py

# Validate data integrity
mongosh ortho_dox validate.js

# Query examples
mongosh ortho_dox --eval 'db.passages.findOne({_id: "Gen_vchap1-1"})'
mongosh ortho_dox --eval 'db.annotations.find({patristic_citations: "BasilG"}).limit(5)'
mongosh ortho_dox --eval 'db.annotations.find({type: "variant"}).limit(5)'
```

## Data Validation

The `validate.js` script performs comprehensive integrity checks on the extracted data. Run it after extraction to verify data quality:

```bash
mongosh ortho_dox validate.js
```

### Validation Checks Performed

| # | Category | What It Checks |
|---|----------|----------------|
| 1 | **Null/Empty Fields** | All required fields populated (text, book_id, type, abbreviations) |
| 2 | **Sequential Integrity** | Missing chapters, missing verses, duplicate verse IDs, zero values |
| 3 | **Referential Integrity** | All book_ids exist, cross-ref targets exist, annotation refs exist |
| 4 | **Bidirectional Consistency** | passage→annotation and annotation→passage links match |
| 5 | **Text Quality** | HTML tags leaked, annotation markers (†‡ω), very short/long text |
| 6 | **Patristic Citations** | All cited sources exist in patristic_sources collection |
| 7 | **Cross-DB Consistency** | ortho_dox and ortho_raw have identical passage/annotation IDs |
| 8 | **Book Structure** | No books without passages, testament assignments correct |
| 9 | **ID Format Validation** | Passage IDs match `{Abbr}_vchap{Ch}-{V}`, annotation IDs match `f{n}`/`fx{n}` |
| 10 | **ID-to-Field Consistency** | Chapter/verse in ID matches fields, abbreviations map to correct books |
| 11 | **Character/Encoding** | No control chars, zero-width chars, unencoded HTML entities, replacement chars |
| 12 | **Duplicate Detection** | Flags identical passage text (parallel passages) and annotation text |
| 13 | **Truncation Detection** | Unbalanced quotes/parentheses, lowercase prose starts |
| 14 | **Expected Chapter Counts** | Validates against known biblical chapter counts (LXX numbering) |
| 15 | **Annotation Consistency** | verse_display matches annotation text start |
| 16 | **Format Distribution** | Poetry/prose ratios for expected book types |
| 17 | **Daniel/Susanna/Bel Split** | Verifies correct separation of multi-text Daniel.html |
| 18 | **Cross-Ref Self-References** | Flags self-referential cross-refs (textual criticism notes) |
| 19 | **Abbreviation Completeness** | All abbreviations in passages map to books, no orphans |
| 20 | **Annotation Density Outliers** | Books with zero annotations when mean is >5% |
| 21 | **Statistics** | Passage distribution, annotation coverage, density by book |

### Interpreting Results

The script outputs two categories:

- **ISSUES** (Critical) - Data integrity problems that must be fixed
- **WARNINGS** (Informational) - Known quirks or edge cases to review

Example output:
```
ISSUES (require attention): 0

WARNINGS (review recommended): 5
  [SEQUENCE] 1 potentially missing verses
    - esther 4:6
  [REF_INTEGRITY] 15 orphan annotations (no linked passages)
    - f1704 - 1:1m-1r (Esther Greek addition)
    - f6257 - Prologue (Sirach)
  ...

✓ NO CRITICAL ISSUES FOUND
```

### Expected Warnings

These warnings are **known and documented** - they are not extraction errors:

| Warning | Count | Explanation |
|---------|-------|-------------|
| `esther 4:6` missing | 1 | Source EPUB omits this verse (TOC links 6→4:5) |
| Orphan annotations | 16 | Esther Greek additions (10), poetry distance (4), Hosea (1), Prologue (1) |
| Very short verses | 5 | Legitimate poetry fragments ("and,", "For") |
| Books <20 verses | 2 | 2 John (13) and 3 John (14) are short epistles |
| **Duplicate passage text** | 87 | Parallel passages (Genesis↔Chronicles genealogies) |
| **Unbalanced quotes** | ~5,100 | Multi-verse speeches spanning verse boundaries |
| **Lowercase starts** | ~3,100 | Verse continuations ("but from the fruit...") |
| **Unbalanced parentheses** | 26 | Parenthetical explanations spanning verses |
| **Self-referential cross-refs** | 8 | Textual criticism notes about manuscript variants |
| **Annotation duplicates** | 6 | Same note for study+liturgical, or verse ranges |
| **Article text not starting with verse** | 47 | Article annotations start with title, not verse ref |
| **Poetry format low %** | 4 books | `format` reflects HTML structure, not literary genre |

## Statistics (Current Extraction)

| Metric | Count |
|--------|-------|
| Books | 78 |
| Passages | 36,008 |
| **Total Annotations** | **7,863** |
| Study notes | 6,290 |
| Liturgical notes | 365 |
| Variant notes | 932 |
| Citation notes | 229 |
| Article notes | 47 |
| Patristic sources | 53 |
| Orphan annotations | 16 (documented edge cases) |
| Passages with cross-ref targets | 282 |
| Passages with annotation markers | 7,412 |
| Broken cross-refs | 0 |
| Duplicate verse IDs | 0 |

### Annotation Linkage

| Type | Total | Linked to Passages | Orphans |
|------|-------|-------------------|---------|
| study | 6,290 | 6,275 | 15 |
| variant | 932 | 932 | 0 |
| liturgical | 365 | 365 | 0 |
| citation | 229 | 228 | 1 |
| article | 47 | 47 | 0 |

### Validation Status

| Check | Status |
|-------|--------|
| Null/empty fields | ✓ Pass |
| Sequential integrity | ✓ Pass (1 EPUB gap: Esther 4:6) |
| Referential integrity | ✓ Pass |
| Bidirectional consistency | ✓ Pass |
| Text quality | ✓ Pass (5 short - documented) |
| Cross-database consistency | ✓ Pass |
| ID format validation | ✓ Pass |
| ID-to-field consistency | ✓ Pass |
| Character/encoding integrity | ✓ Pass |
| Abbreviation mapping | ✓ Pass |

### Known Data Quirks

1. **Esther 4:6** - Missing in source EPUB (TOC links to 4:5, text jumps to 4:7)
2. **Very short verses** - Luke 4:11 ("and,"), Heb 1:10 ("And:"), etc. - legitimate partials
3. **Parallel passage duplicates** - 87 passage pairs have identical text because Genesis genealogies are repeated verbatim in 1 Chronicles. Examples: Gen 10:6 = 1Chr 1:8, Gen 36:34 = 1Chr 1:33
4. **Multi-verse quotations** - ~5,100 passages have unbalanced smart quotes because biblical speeches span verse boundaries. God's words in Gen 1:14 close in Gen 1:15.
5. **Verse continuations** - ~3,100 prose verses start with lowercase because they continue sentences from previous verses ("but from the fruit of the tree...")
6. **Textual criticism cross-refs** - 8 passages have self-referential cross-references that are actually manuscript variant notes (e.g., "NU-Text omits verse 36", "M-Text reverses verses 16 and 17")
7. **Format field semantics** - The `format` field ("prose"/"poetry") indicates HTML element structure, not literary genre. Psalms shows only 2% "poetry" because most verses use inline `<sup>` markers inside `<p>` elements rather than `<ol>` list structures.
8. **LXX Psalm numbering** - Psalms use Septuagint numbering. "The Lord is my shepherd" is Psalm 22 (not 23). Most Psalms are numbered one lower than Protestant Bibles.
9. **Poetry newlines** - 52 Psalm passages contain literal newline characters (`\n`) to preserve poetic line structure from the HTML `<li>` elements. This is intentional.

## Dependencies

- Python 3.10+
- lxml
- beautifulsoup4
- pymongo
- MongoDB (localhost:27017)
