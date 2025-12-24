"""Context service for MCP-focused queries."""

from api.db import MongoDB
from api.models.annotation import AnnotationDetail
from api.models.common import AnnotationType, ExpandMode
from api.models.context import CrossReferences, CrossRefsResponse, PassageContext
from api.models.passage import PassageFull, PassageRef, PatristicCitationExpanded
from api.services import passage_service


async def _fetch_incoming_cross_refs(passage_id: str) -> list[PassageRef]:
    """Find passages that reference the given passage_id."""
    db = MongoDB.db_dox

    # Find passages where cross_ref_targets contains this passage_id
    cursor = db.passages.find(
        {"cross_ref_targets": passage_id},
        {"_id": 1, "book_id": 1, "chapter": 1, "verse": 1, "text": 1},
    )
    docs = await cursor.to_list(length=None)

    if not docs:
        return []

    # Get book names
    book_ids = list({d["book_id"] for d in docs})
    book_cursor = db.books.find({"_id": {"$in": book_ids}}, {"_id": 1, "name": 1})
    books = await book_cursor.to_list(length=None)
    book_names = {b["_id"]: b["name"] for b in books}

    refs = []
    for d in docs:
        text = d.get("text", "")
        preview = text[:100] + "..." if len(text) > 100 else text
        refs.append(
            PassageRef(
                id=d["_id"],
                book_id=d["book_id"],
                book_name=book_names.get(d["book_id"], d["book_id"]),
                chapter=d["chapter"],
                verse=d["verse"],
                preview=preview,
            )
        )

    return refs


async def _collect_patristic_sources(passage: PassageFull) -> list[PatristicCitationExpanded]:
    """Collect unique patristic sources from all annotations in a passage."""
    seen = set()
    sources = []

    # Iterate through all annotation groups
    for ann in passage.annotations.study_notes:
        for pat in ann.patristic_citations:
            if pat.id not in seen:
                seen.add(pat.id)
                sources.append(pat)

    for ann in passage.annotations.liturgical:
        for pat in ann.patristic_citations:
            if pat.id not in seen:
                seen.add(pat.id)
                sources.append(pat)

    return sources


async def _fetch_related_articles(passage_id: str) -> list[AnnotationDetail]:
    """Find article annotations that reference or are linked to this passage."""
    db = MongoDB.db_dox

    # Find articles linked to this passage
    cursor = db.annotations.find(
        {"type": "article", "passage_ids": passage_id},
    )
    docs = await cursor.to_list(length=None)

    articles = []
    for doc in docs:
        articles.append(
            AnnotationDetail(
                id=doc["_id"],
                type=AnnotationType(doc["type"]),
                passage_ids=doc.get("passage_ids", []),
                verse_display=doc.get("verse_display", ""),
                text=doc.get("text", ""),
                patristic_citations=doc.get("patristic_citations", []),
                scripture_refs=doc.get("scripture_refs", []),
            )
        )

    return articles


async def get_passage_context(passage_id: str) -> PassageContext | None:
    """Get full context bundle for a passage."""
    # Get the passage with full expand
    passage = await passage_service.get_passage(
        passage_id, expand=ExpandMode.FULL, include_html=True
    )
    if not passage or not isinstance(passage, PassageFull):
        return None

    # Outgoing refs come from the passage
    outgoing = passage.cross_references.targets

    # Get incoming refs (passages that reference this one)
    incoming = await _fetch_incoming_cross_refs(passage_id)

    # Collect patristic sources from annotations
    patristic_sources = await _collect_patristic_sources(passage)

    # Get related articles
    related_articles = await _fetch_related_articles(passage_id)

    return PassageContext(
        passage=passage,
        cross_references=CrossReferences(outgoing=outgoing, incoming=incoming),
        patristic_sources=patristic_sources,
        related_articles=related_articles,
    )


async def get_cross_refs(passage_id: str) -> CrossRefsResponse | None:
    """Get bidirectional cross-references for a passage."""
    db = MongoDB.db_dox

    # Verify passage exists and get outgoing refs
    doc = await db.passages.find_one(
        {"_id": passage_id},
        {"cross_ref_targets": 1},
    )
    if not doc:
        return None

    # Get outgoing refs as PassageRef objects
    outgoing_ids = doc.get("cross_ref_targets", [])
    outgoing = []
    if outgoing_ids:
        refs_by_id = await passage_service._get_passage_refs_batch(outgoing_ids)
        outgoing = [refs_by_id[rid] for rid in outgoing_ids if rid in refs_by_id]

    # Get incoming refs
    incoming = await _fetch_incoming_cross_refs(passage_id)

    return CrossRefsResponse(
        passage_id=passage_id,
        outgoing=outgoing,
        incoming=incoming,
    )
