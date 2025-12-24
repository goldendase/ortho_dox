"""Annotation and Patristic source query services."""

from api.db import MongoDB
from api.models.annotation import (
    AnnotationDetail,
    AnnotationListResponse,
    PatristicSource,
    PatristicSourceListResponse,
    PatristicSourceWithCount,
)
from api.models.common import AnnotationType


def _doc_to_annotation(doc: dict) -> AnnotationDetail:
    """Convert MongoDB document to AnnotationDetail."""
    return AnnotationDetail(
        id=doc["_id"],
        type=AnnotationType(doc["type"]),
        passage_ids=doc.get("passage_ids", []),
        verse_display=doc.get("verse_display", ""),
        text=doc.get("text", ""),
        patristic_citations=doc.get("patristic_citations", []),
        scripture_refs=doc.get("scripture_refs", []),
    )


async def get_annotation(annotation_id: str) -> AnnotationDetail | None:
    """Get a single annotation by ID."""
    db = MongoDB.db_dox
    doc = await db.annotations.find_one({"_id": annotation_id})
    if not doc:
        return None
    return _doc_to_annotation(doc)


async def get_annotations(
    type: AnnotationType | None = None,
    patristic_source: str | None = None,
    book_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> AnnotationListResponse:
    """Query annotations with filters."""
    db = MongoDB.db_dox

    # Build query
    query = {}
    if type:
        query["type"] = type.value
    if patristic_source:
        query["patristic_citations"] = patristic_source

    # If filtering by book, need to find annotations linked to passages in that book
    if book_id:
        # Get all passage IDs in the book
        passage_cursor = db.passages.find({"book_id": book_id}, {"_id": 1})
        passages = await passage_cursor.to_list(length=None)
        passage_ids = [p["_id"] for p in passages]
        query["passage_ids"] = {"$in": passage_ids}

    # Get total count
    total = await db.annotations.count_documents(query)

    # Get paginated results
    cursor = db.annotations.find(query).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)

    annotations = [_doc_to_annotation(doc) for doc in docs]

    return AnnotationListResponse(
        annotations=annotations,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_patristic_sources() -> PatristicSourceListResponse:
    """Get all patristic sources with citation counts."""
    db = MongoDB.db_dox

    # Get all sources
    cursor = db.patristic_sources.find({})
    sources_raw = await cursor.to_list(length=None)

    # Get citation counts using aggregation
    citation_counts = await db.annotations.aggregate([
        {"$unwind": "$patristic_citations"},
        {"$group": {"_id": "$patristic_citations", "count": {"$sum": 1}}},
    ]).to_list(length=None)

    counts_by_id = {c["_id"]: c["count"] for c in citation_counts}

    sources = [
        PatristicSourceWithCount(
            id=s["_id"],
            name=s["name"],
            citation_count=counts_by_id.get(s["_id"], 0),
        )
        for s in sources_raw
    ]

    # Sort by citation count descending
    sources.sort(key=lambda s: s.citation_count, reverse=True)

    return PatristicSourceListResponse(sources=sources, total=len(sources))


async def get_patristic_source(source_id: str) -> PatristicSource | None:
    """Get a single patristic source by ID."""
    db = MongoDB.db_dox
    doc = await db.patristic_sources.find_one({"_id": source_id})
    if not doc:
        return None
    return PatristicSource(id=doc["_id"], name=doc["name"])


async def get_annotations_by_patristic_source(
    source_id: str,
    limit: int = 100,
    offset: int = 0,
) -> AnnotationListResponse:
    """Get all annotations citing a specific patristic source."""
    db = MongoDB.db_dox

    query = {"patristic_citations": source_id}

    total = await db.annotations.count_documents(query)

    cursor = db.annotations.find(query).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)

    annotations = [_doc_to_annotation(doc) for doc in docs]

    return AnnotationListResponse(
        annotations=annotations,
        total=total,
        limit=limit,
        offset=offset,
    )
