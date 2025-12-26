"""Build upfront context for the chat agent.

This module constructs the reading_context field for the DSPy signature,
providing the LLM with:
- Current reading position with EXPLICIT IDs (so agent never needs to look them up)
- Full content when available (verse text, chapter text, node content)
- Available resources for drilling down (annotations, cross-refs, etc.)

Key principle: The frontend sends explicit content when it has it. We use that
directly and only fetch what's missing. IDs are always explicit so the agent
never has to call list_library_works() or similar just to find an ID.
"""

from api.models.chat import ReadingContext
from api.models.common import ExpandMode
from api.models.library import LibraryExpandMode
from api.services import book_service, context_service, library_service, passage_service


async def build_context(ctx: ReadingContext | None) -> str:
    """Build the upfront context string for the LLM.

    Uses explicit content from frontend when available, fetches only what's missing.
    Always provides explicit IDs so the agent never needs to look them up.
    """
    if not ctx:
        return "No specific reading context provided. The user is asking a general question."

    sections = []

    # OSB Context (Scripture)
    if ctx.passage_id:
        osb_ctx = await _build_passage_context(ctx)
        if osb_ctx:
            sections.append(osb_ctx)
    elif ctx.book_id and ctx.chapter:
        osb_ctx = await _build_chapter_context(ctx)
        if osb_ctx:
            sections.append(osb_ctx)

    # Library Context (Theological Works)
    if ctx.work_id:
        lib_ctx = await _build_library_context(ctx)
        if lib_ctx:
            sections.append(lib_ctx)

    if not sections:
        return "No specific reading context provided. The user is asking a general question."

    return "\n\n".join(sections)


async def _build_passage_context(ctx: ReadingContext) -> str | None:
    """Build context for a specific verse.

    Uses explicit content from ctx when available, fetches annotations/cross-refs.
    """
    passage_id = ctx.passage_id

    # Fetch additional context (annotations, cross-refs, library refs)
    full_ctx = await context_service.get_passage_context(passage_id)
    if not full_ctx:
        # Fall back to explicit context if fetch failed
        if ctx.verse_text and ctx.book_name:
            return _build_minimal_passage_context(ctx)
        return None

    passage = full_ctx.passage

    # Use explicit content from frontend if available, else use fetched
    book_name = ctx.book_name or passage.book_name
    chapter = ctx.chapter or passage.chapter
    verse = ctx.verse or passage.verse
    verse_text = ctx.verse_text or passage.text

    lines = [
        "## OSB (Scripture) Context",
        "",
        f"### Currently Viewing: {book_name} {chapter}:{verse}",
        "",
        "**EXPLICIT IDs FOR TOOLS:**",
        f"- passage_id: `{passage_id}`",
        f"- book_id: `{ctx.book_id or passage.book_id}`",
        f"- chapter: {chapter}",
        f"- verse: {verse}",
        "",
        "**Verse Text:**",
        f'"{verse_text}"',
        "",
    ]

    # Study notes summary
    if passage.annotations and passage.annotations.study_notes:
        note_ids = [n.id for n in passage.annotations.study_notes]
        lines.append(f"**Study Notes Available:** {', '.join(note_ids)}")
        lines.append("  (Use get_study_note tool with these IDs to read full notes)")

        # Collect patristic sources from notes
        fathers = set()
        for note in passage.annotations.study_notes:
            for p in note.patristic_citations:
                name = p.name if hasattr(p, 'name') else str(p)
                fathers.add(name)
        if fathers:
            lines.append(f"**Church Fathers Cited:** {', '.join(sorted(fathers))}")

    # Liturgical references
    if passage.annotations and passage.annotations.liturgical:
        lit_ids = [n.id for n in passage.annotations.liturgical]
        lines.append(f"**Liturgical References:** {', '.join(lit_ids)}")

    # Variants (NT manuscripts)
    if passage.annotations and passage.annotations.variants:
        var_ids = [n.id for n in passage.annotations.variants]
        lines.append(f"**Textual Variants:** {', '.join(var_ids)}")

    # Cross-references
    if full_ctx.cross_references:
        outgoing = full_ctx.cross_references.outgoing
        incoming = full_ctx.cross_references.incoming

        if outgoing:
            refs = [f"{r.book_name} {r.chapter}:{r.verse} (id: `{r.id}`)" for r in outgoing[:8]]
            lines.append(f"**Cross-References (this verse cites):**")
            for ref in refs:
                lines.append(f"  - {ref}")
            if len(outgoing) > 8:
                lines.append(f"  ... and {len(outgoing) - 8} more (use get_connections tool)")

        if incoming:
            refs = [f"{r.book_name} {r.chapter}:{r.verse} (id: `{r.id}`)" for r in incoming[:8]]
            lines.append(f"**Referenced By (other passages citing this):**")
            for ref in refs:
                lines.append(f"  - {ref}")
            if len(incoming) > 8:
                lines.append(f"  ... and {len(incoming) - 8} more (use get_connections tool)")

    # Related articles
    if full_ctx.related_articles:
        article_ids = [a.id for a in full_ctx.related_articles]
        lines.append(f"**Related Articles:** {', '.join(article_ids)}")

    # Library works citing this passage
    if full_ctx.library_refs:
        lines.append("**Library Works Citing This Passage:**")
        for ref in full_ctx.library_refs[:5]:
            author = ref.author if ref.author else "Unknown"
            lines.append(f"  - {ref.work_title} by {author} (work_id: `{ref.work_id}`)")
        if len(full_ctx.library_refs) > 5:
            lines.append(f"  ... and {len(full_ctx.library_refs) - 5} more")

    return "\n".join(lines)


def _build_minimal_passage_context(ctx: ReadingContext) -> str:
    """Build minimal context when full fetch failed but we have explicit content."""
    lines = [
        "## OSB (Scripture) Context",
        "",
        f"### Currently Viewing: {ctx.book_name} {ctx.chapter}:{ctx.verse}",
        "",
        "**EXPLICIT IDs FOR TOOLS:**",
        f"- passage_id: `{ctx.passage_id}`",
        f"- book_id: `{ctx.book_id}`",
        f"- chapter: {ctx.chapter}",
        f"- verse: {ctx.verse}",
        "",
        "**Verse Text:**",
        f'"{ctx.verse_text}"',
        "",
        "(Use get_passage tool with include_annotations=True for study notes)",
    ]
    return "\n".join(lines)


async def _build_chapter_context(ctx: ReadingContext) -> str | None:
    """Build context for a chapter (no specific verse selected).

    If ctx.chapter_text is provided, use it directly. Otherwise fetch.
    """
    book_id = ctx.book_id
    chapter = ctx.chapter

    book = await book_service.get_book(book_id)
    book_name = ctx.book_name or (book.name if book else book_id.title())

    lines = [
        "## OSB (Scripture) Context",
        "",
        f"### Currently Reading: {book_name} Chapter {chapter}",
        "",
        "**EXPLICIT IDs FOR TOOLS:**",
        f"- book_id: `{book_id}`",
        f"- chapter: {chapter}",
        f"- passage_id pattern: `{book_id.title()[:3]}_vchap{chapter}-{{verse}}`",
        "",
    ]

    # Use explicit chapter text if provided
    if ctx.chapter_text:
        chapter_text = ctx.chapter_text
        if len(chapter_text) > 4000:
            chapter_text = chapter_text[:4000] + "\n\n[Chapter text truncated]"
        lines.append("**Full Chapter Text:**")
        lines.append(chapter_text)
        lines.append("")
    else:
        # Fetch preview
        passages, nav = await passage_service.get_chapter_passages(
            book_id, chapter, ExpandMode.NONE, verse_start=1, verse_end=5
        )

        if passages:
            preview_text = " ".join(f"({p.verse}) {p.text}" for p in passages[:5])
            if len(preview_text) > 500:
                preview_text = preview_text[:500] + "..."
            lines.append(f'**Preview (first verses):**')
            lines.append(preview_text)
            lines.append("")
            lines.append("(Use get_chapter tool for full chapter text)")

    # Chapter info
    if book:
        chapter_info = next((c for c in book.chapters if c.chapter == chapter), None)
        if chapter_info:
            lines.append(f"**Verses in Chapter:** {chapter_info.verse_count}")

    lines.append("")
    lines.append("Use get_passage(passage_id, include_annotations=True) for study notes on specific verses.")

    return "\n".join(lines)


async def _build_library_context(ctx: ReadingContext) -> str | None:
    """Build context for a library work or node.

    Uses explicit content from ctx when available, fetches components/refs.
    """
    work_id = ctx.work_id
    node_id = ctx.node_id

    # Get work metadata
    work = await library_service.get_work(work_id)
    work_title = ctx.work_title or (work.title if work else work_id)

    lines = [
        "## Library (Theological Work) Context",
        "",
    ]

    if node_id:
        # Reading a specific section
        node = await library_service.get_node(work_id, node_id, LibraryExpandMode.FULL)

        # Use explicit content or fetched content
        node_title = ctx.node_title or (node.title if node and hasattr(node, 'title') else None)

        lines.extend([
            f"### Currently Reading: {work_title}",
            f"**Section:** {node_title or node_id}",
            "",
            "**EXPLICIT IDs FOR TOOLS:**",
            f"- work_id: `{work_id}`",
            f"- node_id: `{node_id}`",
            "",
        ])

        # Author info
        if work and work.authors:
            author = work.authors[0]
            author_str = author.name
            if author.dates:
                author_str += f" ({author.dates})"
            lines.append(f"**Author:** {author_str}")
            lines.append("")

        # Content - prefer explicit, fall back to fetched
        content = ctx.node_content
        if not content and node and hasattr(node, 'content') and node.content:
            content = node.content

        # If user selected a specific paragraph, show that prominently
        if ctx.paragraph_text:
            lines.append("**Selected Paragraph:**")
            para_text = ctx.paragraph_text
            if len(para_text) > 1000:
                para_text = para_text[:1000] + "..."
            lines.append(f'"{para_text}"')
            lines.append("")
            lines.append("**Full Section Content:**")
        else:
            lines.append("**Section Content:**")

        if content:
            if len(content) > 4000:
                content = content[:4000] + "\n\n[Content truncated]"
            lines.append(content)
            lines.append("")

        # Components from fetched node (footnotes, etc.)
        if node and hasattr(node, 'components') and node.components:
            comps = node.components

            # Footnotes
            if comps.footnotes:
                lines.append("**Footnotes in this section:**")
                for fn in comps.footnotes[:10]:
                    fn_content = fn.content
                    if len(fn_content) > 200:
                        fn_content = fn_content[:200] + "..."
                    lines.append(f"  [{fn.marker}] {fn_content}")
                if len(comps.footnotes) > 10:
                    lines.append(f"  ... and {len(comps.footnotes) - 10} more footnotes")
                lines.append("")

            # Endnotes
            if comps.endnotes:
                lines.append("**Endnotes in this section:**")
                for en in comps.endnotes[:5]:
                    en_content = en.content
                    if len(en_content) > 200:
                        en_content = en_content[:200] + "..."
                    lines.append(f"  [{en.marker}] {en_content}")
                if len(comps.endnotes) > 5:
                    lines.append(f"  ... and {len(comps.endnotes) - 5} more endnotes")
                lines.append("")

        # Scripture references in this section
        if node and hasattr(node, 'scripture_refs') and node.scripture_refs:
            lines.append("**Scripture References in this section:**")
            for ref in node.scripture_refs[:15]:
                book_name = ref.book_name if hasattr(ref, 'book_name') else ""
                chapter = ref.chapter if hasattr(ref, 'chapter') else ""
                verse = ref.verse_start if hasattr(ref, 'verse_start') else ""
                passage_id = ref.passage_id if hasattr(ref, 'passage_id') else ""
                lines.append(f"  - {book_name} {chapter}:{verse} (passage_id: `{passage_id}`)")
            if len(node.scripture_refs) > 15:
                lines.append(f"  ... and {len(node.scripture_refs) - 15} more")
            lines.append("")

        # Navigation
        if node and hasattr(node, 'navigation') and node.navigation:
            nav = node.navigation
            if nav.prev:
                lines.append(f"**Previous Section:** {nav.prev.title or nav.prev.id} (node_id: `{nav.prev.id}`)")
            if nav.next:
                lines.append(f"**Next Section:** {nav.next.title or nav.next.id} (node_id: `{nav.next.id}`)")

    else:
        # Just viewing work overview (no specific node)
        lines.extend([
            f"### Currently Viewing: {work_title}",
            "",
            "**EXPLICIT IDs FOR TOOLS:**",
            f"- work_id: `{work_id}`",
            "",
        ])

        if work:
            if work.subtitle:
                lines.append(f"*{work.subtitle}*")
                lines.append("")

            if work.authors:
                author = work.authors[0]
                author_str = author.name
                if author.dates:
                    author_str += f" ({author.dates})"
                lines.append(f"**Author:** {author_str}")

            lines.append(f"**Category:** {work.category}")
            if work.subjects:
                lines.append(f"**Subjects:** {', '.join(work.subjects)}")

            lines.append(f"**Sections:** {work.node_count}")
            lines.append(f"**Scripture References:** {work.scripture_ref_count}")

        lines.append("")
        lines.append("Use get_work_toc(work_id) to see table of contents, then get_library_content(work_id, node_id) to read sections.")

    return "\n".join(lines)
