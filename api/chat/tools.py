"""Focused tools for the OSB chat agent.

Each tool returns formatted text (not JSON dumps) optimized for LLM consumption.
Tools are designed to drill down into specific items identified in the upfront context.

Key principle: Return what the LLM needs to formulate a response, not raw data structures.
"""

import dspy

from api.models.common import AnnotationType, ExpandMode
from api.models.library import LibraryExpandMode
from api.services import annotation_service, book_service, context_service, library_service, passage_service, vector_search_service


async def get_passage(passage_id: str, include_annotations: bool = False) -> str:
    """
    Get a Bible passage by ID.

    Use this to read the text of a verse or to get the full study notes for a passage.
    Passage IDs are formatted like 'Gen_vchap1-1' (Genesis 1:1) or 'Matt_vchap5-3' (Matthew 5:3).

    Args:
        passage_id: The passage ID (e.g., 'Gen_vchap1-1', 'John_vchap3-16')
        include_annotations: Set True to include study notes and patristic commentary

    Returns:
        Formatted passage text, optionally with annotations
    """
    expand = ExpandMode.ANNOTATIONS if include_annotations else ExpandMode.NONE
    passage = await passage_service.get_passage(passage_id, expand=expand, include_html=False)

    if not passage:
        return f"Passage not found: {passage_id}"

    lines = [
        f"**{passage.book_name} {passage.chapter}:{passage.verse}**",
        "",
        passage.text,
    ]

    if include_annotations and hasattr(passage, 'annotations') and passage.annotations:
        # Study notes
        if passage.annotations.study_notes:
            lines.append("")
            lines.append("---")
            lines.append("**Study Notes:**")
            for note in passage.annotations.study_notes:
                lines.append("")
                lines.append(f"[{note.id}] {note.text}")
                if note.patristic_citations:
                    fathers = []
                    for p in note.patristic_citations:
                        name = p.name if hasattr(p, 'name') else str(p)
                        fathers.append(name)
                    lines.append(f"  *Sources: {', '.join(fathers)}*")

        # Variants
        if passage.annotations.variants:
            lines.append("")
            lines.append("**Textual Variants:**")
            for var in passage.annotations.variants:
                lines.append(f"[{var.id}] {var.text}")

        # Liturgical
        if passage.annotations.liturgical:
            lines.append("")
            lines.append("**Liturgical Usage:**")
            for lit in passage.annotations.liturgical:
                lines.append(f"[{lit.id}] {lit.text}")

    return "\n".join(lines)


async def get_chapter(book_id: str, chapter: int, verse_start: int | None = None, verse_end: int | None = None) -> str:
    """
    Get all verses in a chapter or a verse range.

    Use this to read through a section of Scripture or to get context around a specific verse.
    Book IDs are lowercase without spaces: 'genesis', 'matthew', 'psalms', '1corinthians'.

    Args:
        book_id: Lowercase book ID (e.g., 'genesis', 'matthew', 'psalms')
        chapter: Chapter number
        verse_start: Optional starting verse (default: 1)
        verse_end: Optional ending verse (default: last verse)

    Returns:
        Formatted chapter text with verse numbers
    """
    passages, nav = await passage_service.get_chapter_passages(
        book_id, chapter, ExpandMode.NONE, verse_start=verse_start, verse_end=verse_end
    )

    if not passages:
        return f"Chapter not found: {book_id} {chapter}"

    book_name = passages[0].book_name if passages else book_id.title()

    lines = [f"**{book_name} {chapter}**", ""]

    for passage in passages:
        lines.append(f"**{passage.verse}** {passage.text}")

    # Navigation hints
    if nav:
        lines.append("")
        nav_parts = []
        if nav.prev_chapter:
            lines.append(f"*Previous: {book_name} {chapter - 1}*")
        if nav.next_chapter:
            lines.append(f"*Next: {book_name} {chapter + 1}*")

    return "\n".join(lines)


async def get_study_note(note_id: str) -> str:
    """
    Get the full text of a specific study note.

    Study note IDs are like 'f1', 'f23', etc. Use this when the user asks about
    a specific annotation or when you need the full text of a note mentioned in context.

    Args:
        note_id: The annotation ID (e.g., 'f1', 'f42', 'fx5')

    Returns:
        Full study note text with sources
    """
    annotation = await annotation_service.get_annotation(note_id)

    if not annotation:
        return f"Annotation not found: {note_id}"

    lines = [
        f"**Study Note {note_id}** (verse {annotation.verse_display})",
        "",
        annotation.text,
    ]

    # Patristic sources
    if annotation.patristic_citations:
        lines.append("")
        fathers = []
        for p in annotation.patristic_citations:
            name = p.name if hasattr(p, 'name') else str(p)
            fathers.append(name)
        lines.append(f"*Church Fathers cited: {', '.join(fathers)}*")

    # Scripture refs within the note
    if annotation.scripture_refs:
        refs = []
        for ref in annotation.scripture_refs:
            display = ref.display if hasattr(ref, 'display') else str(ref)
            refs.append(display)
        lines.append(f"*Scripture references: {', '.join(refs)}*")

    return "\n".join(lines)


async def get_connections(passage_id: str) -> str:
    """
    Get cross-references and library works that cite this passage.

    Use this to explore how a passage connects to other Scripture and to theological writings.
    Shows both passages this verse references AND passages that reference this verse.

    Args:
        passage_id: The passage ID to get connections for

    Returns:
        Cross-references (bidirectional) and library citations
    """
    # Get cross-refs
    cross_refs = await context_service.get_cross_refs(passage_id)
    # Get library refs
    lib_refs = await library_service.get_library_refs_for_passage(passage_id)

    lines = [f"**Connections for {passage_id}**", ""]

    if cross_refs:
        if cross_refs.outgoing:
            lines.append("**This passage references:**")
            for ref in cross_refs.outgoing:
                preview = ref.preview[:80] + "..." if len(ref.preview) > 80 else ref.preview
                lines.append(f"- {ref.book_name} {ref.chapter}:{ref.verse}: \"{preview}\"")
            lines.append("")

        if cross_refs.incoming:
            lines.append("**Referenced by (other passages that cite this one):**")
            for ref in cross_refs.incoming:
                preview = ref.preview[:80] + "..." if len(ref.preview) > 80 else ref.preview
                lines.append(f"- {ref.book_name} {ref.chapter}:{ref.verse}: \"{preview}\"")
            lines.append("")

    if lib_refs and lib_refs.library_refs:
        lines.append("**Library works citing this passage:**")
        for ref in lib_refs.library_refs:
            author = ref.author.name if ref.author else "Unknown"
            lines.append(f"- **{ref.work_title}** by {author}")
            if ref.node_title:
                lines.append(f"  Chapter: {ref.node_title}")
            if ref.context_snippet:
                lines.append(f"  \"{ref.context_snippet}\"")
        lines.append("")

    if len(lines) == 2:  # Only header added
        lines.append("No cross-references or library citations found for this passage.")

    return "\n".join(lines)


async def search_annotations(
    annotation_type: str | None = None,
    patristic_source: str | None = None,
    book_id: str | None = None,
    limit: int = 15,
) -> str:
    """
    Search study notes and annotations.

    Use this to find what the Church Fathers say about topics, or to explore
    annotations in a specific book.

    Annotation types:
    - 'study': Patristic commentary and theological notes (most common)
    - 'liturgical': Liturgical usage references
    - 'variant': NT manuscript variants
    - 'citation': Cross-reference notes
    - 'article': Topical study articles

    Patristic source IDs: 'JohnChr' (Chrysostom), 'BasilG' (Basil the Great),
    'AugHip' (Augustine), 'CyrAl' (Cyril of Alexandria), 'GregNaz' (Gregory the Theologian)

    Args:
        annotation_type: Type filter ('study', 'liturgical', 'variant', 'citation', 'article')
        patristic_source: Church Father ID (e.g., 'JohnChr', 'BasilG')
        book_id: Limit search to a book (e.g., 'genesis', 'matthew')
        limit: Max results (default 15)

    Returns:
        Matching annotations with verse references
    """
    ann_type = AnnotationType(annotation_type) if annotation_type else None
    limit = min(limit, 30)  # Cap at 30

    result = await annotation_service.get_annotations(
        type=ann_type,
        patristic_source=patristic_source,
        book_id=book_id,
        limit=limit,
        offset=0,
    )

    # Build search description
    search_parts = []
    if annotation_type:
        search_parts.append(f"type={annotation_type}")
    if patristic_source:
        search_parts.append(f"father={patristic_source}")
    if book_id:
        search_parts.append(f"book={book_id}")
    search_desc = ", ".join(search_parts) if search_parts else "all"

    lines = [
        f"**Annotation Search** ({search_desc})",
        f"Found {result.total} total, showing {len(result.annotations)}:",
        "",
    ]

    for ann in result.annotations:
        # Truncate long text
        text = ann.text
        if len(text) > 200:
            text = text[:200] + "..."

        lines.append(f"**[{ann.id}]** (verse {ann.verse_display})")
        lines.append(text)

        if ann.patristic_citations:
            fathers = []
            for p in ann.patristic_citations:
                name = p if isinstance(p, str) else str(p)
                fathers.append(name)
            lines.append(f"  *Sources: {', '.join(fathers)}*")
        lines.append("")

    if result.total > limit:
        lines.append(f"*{result.total - limit} more results available. Refine your search or increase limit.*")

    return "\n".join(lines)


async def list_library_works() -> str:
    """
    List all available works in the theological library.

    Use this to discover what texts are available. Returns work IDs that can be
    used with get_work_toc or get_library_content.

    Returns:
        List of available works with titles, authors, and IDs
    """
    result = await library_service.get_works(limit=100)

    if not result.works:
        return "No works available in the library."

    lines = [
        "**Theological Library**",
        f"*{result.total} works available*",
        "",
    ]

    for work in result.works:
        author_str = ""
        if work.authors:
            names = [a.name for a in work.authors]
            author_str = f" by {', '.join(names)}"

        lines.append(f"- **{work.title}**{author_str}")
        lines.append(f"  ID: `{work.id}`")
        if work.subjects:
            lines.append(f"  Topics: {', '.join(work.subjects[:3])}")
        lines.append("")

    lines.append("*Use get_work_toc(work_id) to see the table of contents for any work.*")

    return "\n".join(lines)


async def get_work_toc(work_id: str) -> str:
    """
    Get the table of contents for a library work.

    Returns a clean outline of all sections/chapters with their IDs for navigation.
    Use this to explore what's in a work before reading specific sections.

    Args:
        work_id: The work ID (e.g., 'on-acquisition-holy-spirit')

    Returns:
        Table of contents with section titles and IDs for use with get_library_content
    """
    toc = await library_service.get_work_toc(work_id)
    if not toc:
        return f"Work not found: {work_id}"

    work = await library_service.get_work(work_id)
    work_title = work.title if work else work_id

    lines = [
        f"**{work_title}**",
        "*Table of Contents*",
        "",
    ]

    def render_toc(node, depth=0):
        indent = "  " * depth
        title = node.title or node.label or node.id
        # Clean output: just title and ID, skip internal metadata
        lines.append(f"{indent}- {title}")
        lines.append(f"{indent}  id: `{node.id}`")
        for child in node.children:
            render_toc(child, depth + 1)

    render_toc(toc.root)

    lines.append("")
    lines.append("*Use get_library_content(work_id, node_id) to read a specific section.*")

    return "\n".join(lines)


async def get_library_content(work_id: str, node_id: str) -> str:
    """
    Read content from a specific section of a library work.

    The library contains patristic texts, biographies, and spiritual writings.
    Use get_work_toc first to find the node_id you want to read.

    Args:
        work_id: The work ID (e.g., 'on-acquisition-holy-spirit')
        node_id: The section/chapter ID from the table of contents

    Returns:
        The section content with any footnotes
    """
    # Get specific node content
    node = await library_service.get_node(work_id, node_id, LibraryExpandMode.COMPONENTS)
    if not node:
        return f"Node not found: {work_id}/{node_id}"

    work = await library_service.get_work(work_id)
    work_title = work.title if work else work_id

    lines = [f"**{work_title}**"]
    if hasattr(node, 'title') and node.title:
        lines.append(f"*{node.title}*")
    lines.append("")

    # Content
    if hasattr(node, 'content') and node.content:
        lines.append(node.content)
    else:
        lines.append("*This is a container node without content. Use get_work_toc to find readable sections.*")

    # Components (footnotes, etc.)
    if hasattr(node, 'components') and node.components:
        comps = node.components
        if comps.footnotes:
            lines.append("")
            lines.append("**Footnotes:**")
            for fn in comps.footnotes:
                lines.append(f"[{fn.marker}] {fn.content}")

    # Navigation
    if hasattr(node, 'navigation') and node.navigation:
        nav = node.navigation
        lines.append("")
        if nav.prev:
            lines.append(f"Previous: {nav.prev.title or nav.prev.id} (id: `{nav.prev.id}`)")
        if nav.next:
            lines.append(f"Next: {nav.next.title or nav.next.id} (id: `{nav.next.id}`)")

    return "\n".join(lines)


async def search_osb_content(query: str) -> str:
    """
    Semantic search across OSB study notes, articles, and Scripture text.

    Use this when the user asks about a theological topic, doctrine, or theme and you need
    to find relevant study notes or Scripture passages. Returns up to 5 results above the relevance threshold.

    Args:
        query: Natural language search query — specify subject + type of answer sought.
               Good: "Jacob's Ladder typology", "fasting ascetic practice"
               Bad: "Jacob's Ladder typology Christ Theotokos" (pre-judges the answer)

    Returns:
        Relevant results with source type, IDs for follow-up, and full chunk text
    """
    results = await vector_search_service.search_osb(query, top_k=5)

    if not results:
        return f"No OSB results found for: {query}"

    lines = [
        f"**OSB Semantic Search:** \"{query}\"",
        f"Found {len(results)} relevant results:",
        "",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"**[{i}] {r.source_type}** (score: {r.score:.3f})")

        # Provide the right IDs based on source type
        if r.source_type == "osb_study":
            lines.append(f"  - annotation_id: `{r.annotation_id}` (use get_study_note to read full note)")
            if r.book_name and r.chapter:
                verse_display = f"{r.verse_start}" if r.verse_start else ""
                if r.verse_end and r.verse_end != r.verse_start:
                    verse_display += f"-{r.verse_end}"
                lines.append(f"  - passage: {r.book_name} {r.chapter}:{verse_display}")
            if r.passage_ids:
                lines.append(f"  - passage_ids: {r.passage_ids[:3]}{'...' if len(r.passage_ids) > 3 else ''}")

        elif r.source_type == "osb_article":
            lines.append(f"  - annotation_id: `{r.annotation_id}` (use get_study_note to read full article)")

        elif r.source_type == "osb_chapter":
            lines.append(f"  - book_id: `{r.book_id}`, chapter: {r.chapter}")
            lines.append(f"  - (use get_chapter to read full chapter)")

        # Full chunk text (chunks are pre-sized ~1500 chars from ETL)
        lines.append(f"  **Text:** {r.text}")
        lines.append("")

    return "\n".join(lines)


async def search_library_content(query: str) -> str:
    """
    Semantic search across the theological library (patristic works, spiritual texts).

    Use this when the user asks "What do the Fathers say about X?" or when you need
    to find relevant patristic commentary on a topic. Returns up to 5 chunks above the relevance threshold.

    Args:
        query: Natural language search query — specify subject + type of answer sought.
               Good: "Jesus Prayer hesychast practice", "humility patristic teaching"
               Bad: "humility pride spiritual warfare" (too many concepts)

    Returns:
        Relevant chunks with work/node IDs and full chunk text
    """
    results = await vector_search_service.search_library(query, top_k=5)

    if not results:
        return f"No library results found for: {query}"

    lines = [
        f"**Library Semantic Search:** \"{query}\"",
        f"Found {len(results)} relevant results:",
        "",
    ]

    for i, r in enumerate(results, 1):
        title = r.node_title or r.node_id
        lines.append(f"**[{i}] {title}** (score: {r.score:.3f})")
        lines.append(f"  - work_id: `{r.work_id}`")
        lines.append(f"  - node_id: `{r.node_id}` (use get_library_content for full section)")
        if r.author_id:
            lines.append(f"  - author_id: `{r.author_id}`")
        if r.scripture_refs:
            refs = r.scripture_refs[:5]
            lines.append(f"  - scripture_refs: {refs}{'...' if len(r.scripture_refs) > 5 else ''}")

        # Full chunk text (chunks are pre-sized ~1500 chars from ETL)
        lines.append(f"  **Text:** {r.text}")
        lines.append("")

    lines.append("*Use get_library_content(work_id, node_id) if you need surrounding context.*")

    return "\n".join(lines)


# Build the TOOLS list for DSPy
TOOLS = [
    dspy.Tool(
        func=get_passage,
        name="get_passage",
        desc="Get a Bible passage by ID. Set include_annotations=True for study notes.",
    ),
    dspy.Tool(
        func=get_chapter,
        name="get_chapter",
        desc="Get all verses in a chapter or verse range.",
    ),
    dspy.Tool(
        func=get_study_note,
        name="get_study_note",
        desc="Get the full text of a specific study note by ID (e.g., 'f1', 'f42').",
    ),
    dspy.Tool(
        func=get_connections,
        name="get_connections",
        desc="Get cross-references and library works citing a passage.",
    ),
    dspy.Tool(
        func=search_annotations,
        name="search_annotations",
        desc="Search annotations by type, Church Father, or book.",
    ),
    dspy.Tool(
        func=list_library_works,
        name="list_library_works",
        desc="List all available works in the theological library with IDs.",
    ),
    dspy.Tool(
        func=get_work_toc,
        name="get_work_toc",
        desc="Get the table of contents for a library work to find section IDs.",
    ),
    dspy.Tool(
        func=get_library_content,
        name="get_library_content",
        desc="Read content from a specific section of a library work.",
    ),
    dspy.Tool(
        func=search_osb_content,
        name="search_osb_content",
        desc="Semantic search across OSB study notes, articles, and Scripture. Use for theological topics.",
    ),
    dspy.Tool(
        func=search_library_content,
        name="search_library_content",
        desc="Semantic search across patristic works. Use when asked 'What do the Fathers say about X?'",
    ),
]
