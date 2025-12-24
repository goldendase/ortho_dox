"""Passage query service with expand mode support."""

import re

from api.db import MongoDB
from api.models.common import AnnotationType, ExpandMode, Format
from api.models.passage import (
    AnnotationEmbed,
    AnnotationEmbedFull,
    AnnotationMarker,
    AnnotationsGroup,
    AnnotationsGroupFull,
    ChapterNavigation,
    CrossReferenceData,
    NavigationLinks,
    PassageFull,
    PassageMinimal,
    PassageRef,
    PassageWithAnnotations,
    PatristicCitationExpanded,
    ScriptureRefDisplay,
)

# Pattern to parse passage IDs like "Gen_vchap1-1" or "P2et_vchap2-6"
PASSAGE_ID_PATTERN = re.compile(r"^([A-Za-z0-9]+)_vchap(\d+)-(\d+)$")


def _parse_passage_id(passage_id: str) -> tuple[str, int, int] | None:
    """Parse passage ID to (abbreviation, chapter, verse). Returns None if invalid."""
    match = PASSAGE_ID_PATTERN.match(passage_id)
    if match:
        return match.group(1), int(match.group(2)), int(match.group(3))
    return None


def _doc_to_minimal(doc: dict) -> PassageMinimal:
    """Convert MongoDB document to PassageMinimal."""
    return PassageMinimal(
        id=doc["_id"],
        book_id=doc["book_id"],
        chapter=doc["chapter"],
        verse=doc["verse"],
        text=doc.get("text", ""),
        format=Format(doc.get("format", "prose")),
        study_note_ids=doc.get("study_note_ids", []),
        liturgical_ids=doc.get("liturgical_ids", []),
        variant_ids=doc.get("variant_ids", []),
        citation_ids=doc.get("citation_ids", []),
        article_ids=doc.get("article_ids", []),
        cross_ref_targets=doc.get("cross_ref_targets", []),
    )


def _doc_to_marker(marker: dict) -> AnnotationMarker:
    """Convert marker dict to AnnotationMarker."""
    return AnnotationMarker(
        id=marker["id"],
        type=AnnotationType(marker["type"]),
        preceding=marker.get("preceding", ""),
    )


async def _build_scripture_refs_display(
    scripture_refs: list[str],
    book_names_by_abbrev: dict[str, str],
) -> list[ScriptureRefDisplay]:
    """Convert scripture ref IDs to display objects."""
    results = []
    for ref_id in scripture_refs:
        parsed = _parse_passage_id(ref_id)
        if parsed:
            abbrev, chapter, verse = parsed
            book_name = book_names_by_abbrev.get(abbrev, abbrev)
            display = f"{book_name} {chapter}:{verse}"
            results.append(ScriptureRefDisplay(id=ref_id, display=display))
        else:
            # Fallback for unparseable IDs
            results.append(ScriptureRefDisplay(id=ref_id, display=ref_id))
    return results


def _annotation_to_embed(
    ann: dict, book_names_by_abbrev: dict[str, str]
) -> AnnotationEmbed:
    """Convert annotation document to AnnotationEmbed."""
    scripture_refs = []
    for ref_id in ann.get("scripture_refs", []):
        parsed = _parse_passage_id(ref_id)
        if parsed:
            abbrev, chapter, verse = parsed
            book_name = book_names_by_abbrev.get(abbrev, abbrev)
            display = f"{book_name} {chapter}:{verse}"
            scripture_refs.append(ScriptureRefDisplay(id=ref_id, display=display))
        else:
            scripture_refs.append(ScriptureRefDisplay(id=ref_id, display=ref_id))

    return AnnotationEmbed(
        id=ann["_id"],
        type=AnnotationType(ann["type"]),
        verse_display=ann.get("verse_display", ""),
        text=ann.get("text", ""),
        patristic_citations=ann.get("patristic_citations", []),
        scripture_refs=scripture_refs,
    )


def _annotation_to_embed_full(
    ann: dict,
    patristic_map: dict[str, str],
    book_names_by_abbrev: dict[str, str],
) -> AnnotationEmbedFull:
    """Convert annotation document to AnnotationEmbedFull with expanded patristic names."""
    citations = [
        PatristicCitationExpanded(id=pid, name=patristic_map.get(pid, pid))
        for pid in ann.get("patristic_citations", [])
    ]

    scripture_refs = []
    for ref_id in ann.get("scripture_refs", []):
        parsed = _parse_passage_id(ref_id)
        if parsed:
            abbrev, chapter, verse = parsed
            book_name = book_names_by_abbrev.get(abbrev, abbrev)
            display = f"{book_name} {chapter}:{verse}"
            scripture_refs.append(ScriptureRefDisplay(id=ref_id, display=display))
        else:
            scripture_refs.append(ScriptureRefDisplay(id=ref_id, display=ref_id))

    return AnnotationEmbedFull(
        id=ann["_id"],
        type=AnnotationType(ann["type"]),
        verse_display=ann.get("verse_display", ""),
        text=ann.get("text", ""),
        patristic_citations=citations,
        scripture_refs=scripture_refs,
    )


def _group_annotations(
    annotations: list[dict], book_names_by_abbrev: dict[str, str]
) -> AnnotationsGroup:
    """Group annotations by type."""
    group = AnnotationsGroup()
    for ann in annotations:
        embed = _annotation_to_embed(ann, book_names_by_abbrev)
        match ann["type"]:
            case "study":
                group.study_notes.append(embed)
            case "liturgical":
                group.liturgical.append(embed)
            case "variant":
                group.variants.append(embed)
            case "citation":
                group.citations.append(embed)
            case "article":
                group.articles.append(embed)
    return group


def _group_annotations_full(
    annotations: list[dict],
    patristic_map: dict[str, str],
    book_names_by_abbrev: dict[str, str],
) -> AnnotationsGroupFull:
    """Group annotations by type with expanded patristic citations."""
    group = AnnotationsGroupFull()
    for ann in annotations:
        embed = _annotation_to_embed_full(ann, patristic_map, book_names_by_abbrev)
        match ann["type"]:
            case "study":
                group.study_notes.append(embed)
            case "liturgical":
                group.liturgical.append(embed)
            case "variant":
                group.variants.append(embed)
            case "citation":
                group.citations.append(embed)
            case "article":
                group.articles.append(embed)
    return group


async def _fetch_annotations(annotation_ids: list[str]) -> list[dict]:
    """Batch fetch annotations by IDs."""
    if not annotation_ids:
        return []
    db = MongoDB.db_dox
    cursor = db.annotations.find({"_id": {"$in": annotation_ids}})
    return await cursor.to_list(length=None)


async def _fetch_patristic_map() -> dict[str, str]:
    """Fetch all patristic sources as id->name map."""
    db = MongoDB.db_dox
    cursor = db.patristic_sources.find({}, {"_id": 1, "name": 1})
    sources = await cursor.to_list(length=None)
    return {s["_id"]: s["name"] for s in sources}


async def _fetch_book_names_by_abbrev() -> dict[str, str]:
    """Fetch abbreviation -> book name mapping."""
    db = MongoDB.db_dox
    cursor = db.books.find({}, {"_id": 1, "name": 1, "abbreviations": 1})
    books = await cursor.to_list(length=None)
    result = {}
    for b in books:
        for abbrev in b.get("abbreviations", []):
            result[abbrev] = b["name"]
    return result


async def _fetch_book_names(book_ids: list[str]) -> dict[str, str]:
    """Fetch book names by IDs."""
    if not book_ids:
        return {}
    db = MongoDB.db_dox
    cursor = db.books.find({"_id": {"$in": book_ids}}, {"_id": 1, "name": 1})
    books = await cursor.to_list(length=None)
    return {b["_id"]: b["name"] for b in books}


async def _fetch_books_ordered() -> list[dict]:
    """Fetch all books ordered by canonical order."""
    db = MongoDB.db_dox
    cursor = db.books.find({}, {"_id": 1, "name": 1, "order": 1}).sort("order", 1)
    return await cursor.to_list(length=None)


async def _get_passage_refs_batch(
    all_passage_ids: list[str],
) -> dict[str, list[PassageRef]]:
    """Batch fetch PassageRef objects, returns dict keyed by source passage ID."""
    if not all_passage_ids:
        return {}

    unique_ids = list(set(all_passage_ids))
    db = MongoDB.db_dox
    cursor = db.passages.find(
        {"_id": {"$in": unique_ids}},
        {"_id": 1, "book_id": 1, "chapter": 1, "verse": 1, "text": 1},
    )
    passages = await cursor.to_list(length=None)

    # Get book names
    book_ids = list({p["book_id"] for p in passages})
    book_names = await _fetch_book_names(book_ids)

    # Build lookup
    refs_by_id = {}
    for p in passages:
        text = p.get("text", "")
        preview = text[:100] + "..." if len(text) > 100 else text
        refs_by_id[p["_id"]] = PassageRef(
            id=p["_id"],
            book_id=p["book_id"],
            book_name=book_names.get(p["book_id"], p["book_id"]),
            chapter=p["chapter"],
            verse=p["verse"],
            preview=preview,
        )

    return refs_by_id


async def _get_navigation_cross_book(
    passage_doc: dict, books_ordered: list[dict]
) -> NavigationLinks:
    """Get prev/next passage IDs, crossing book boundaries."""
    db = MongoDB.db_dox
    book_id = passage_doc["book_id"]
    chapter = passage_doc["chapter"]
    verse = passage_doc["verse"]

    # Build book order lookup
    book_order = {b["_id"]: i for i, b in enumerate(books_ordered)}
    current_order = book_order.get(book_id, 0)

    # Previous passage - first try within book
    prev_passage = await db.passages.find_one(
        {"book_id": book_id, "$or": [
            {"chapter": chapter, "verse": {"$lt": verse}},
            {"chapter": {"$lt": chapter}},
        ]},
        {"_id": 1},
        sort=[("chapter", -1), ("verse", -1)],
    )

    # If no prev in current book, try previous book's last verse
    if not prev_passage and current_order > 0:
        prev_book = books_ordered[current_order - 1]
        prev_passage = await db.passages.find_one(
            {"book_id": prev_book["_id"]},
            {"_id": 1},
            sort=[("chapter", -1), ("verse", -1)],
        )

    # Next passage - first try within book
    next_passage = await db.passages.find_one(
        {"book_id": book_id, "$or": [
            {"chapter": chapter, "verse": {"$gt": verse}},
            {"chapter": {"$gt": chapter}},
        ]},
        {"_id": 1},
        sort=[("chapter", 1), ("verse", 1)],
    )

    # If no next in current book, try next book's first verse
    if not next_passage and current_order < len(books_ordered) - 1:
        next_book = books_ordered[current_order + 1]
        next_passage = await db.passages.find_one(
            {"book_id": next_book["_id"]},
            {"_id": 1},
            sort=[("chapter", 1), ("verse", 1)],
        )

    return NavigationLinks(
        prev=prev_passage["_id"] if prev_passage else None,
        next=next_passage["_id"] if next_passage else None,
    )


async def _get_chapter_navigation(
    book_id: str, chapter: int, chapter_count: int, books_ordered: list[dict]
) -> ChapterNavigation:
    """Get prev/next chapter navigation, crossing book boundaries."""
    book_order = {b["_id"]: i for i, b in enumerate(books_ordered)}
    current_order = book_order.get(book_id, 0)

    prev_chapter = None
    next_chapter = None

    # Previous chapter
    if chapter > 1:
        prev_chapter = f"/books/{book_id}/chapters/{chapter - 1}/passages"
    elif current_order > 0:
        # Go to last chapter of previous book
        prev_book = books_ordered[current_order - 1]
        # Get chapter count for previous book
        db = MongoDB.db_dox
        max_ch = await db.passages.find_one(
            {"book_id": prev_book["_id"]},
            {"chapter": 1},
            sort=[("chapter", -1)],
        )
        if max_ch:
            prev_chapter = f"/books/{prev_book['_id']}/chapters/{max_ch['chapter']}/passages"

    # Next chapter
    if chapter < chapter_count:
        next_chapter = f"/books/{book_id}/chapters/{chapter + 1}/passages"
    elif current_order < len(books_ordered) - 1:
        # Go to first chapter of next book
        next_book = books_ordered[current_order + 1]
        next_chapter = f"/books/{next_book['_id']}/chapters/1/passages"

    return ChapterNavigation(prev_chapter=prev_chapter, next_chapter=next_chapter)


async def _get_html(passage_id: str) -> str | None:
    """Get raw HTML from ortho_raw database."""
    db = MongoDB.db_raw
    doc = await db.passages.find_one({"_id": passage_id}, {"html": 1})
    return doc.get("html") if doc else None


async def get_passage(
    passage_id: str,
    expand: ExpandMode = ExpandMode.NONE,
    include_html: bool = False,
) -> PassageMinimal | PassageWithAnnotations | PassageFull | None:
    """Get a single passage with specified expand mode."""
    db = MongoDB.db_dox

    doc = await db.passages.find_one({"_id": passage_id})
    if not doc:
        return None

    if expand == ExpandMode.NONE:
        return _doc_to_minimal(doc)

    # Fetch book abbreviation mappings for scripture refs
    book_names_by_abbrev = await _fetch_book_names_by_abbrev()

    # Collect all annotation IDs
    all_ann_ids = (
        doc.get("study_note_ids", [])
        + doc.get("liturgical_ids", [])
        + doc.get("variant_ids", [])
        + doc.get("citation_ids", [])
        + doc.get("article_ids", [])
    )

    annotations = await _fetch_annotations(all_ann_ids)
    markers = [_doc_to_marker(m) for m in doc.get("annotation_markers", [])]

    if expand == ExpandMode.ANNOTATIONS:
        minimal = _doc_to_minimal(doc)
        return PassageWithAnnotations(
            **minimal.model_dump(),
            annotations=_group_annotations(annotations, book_names_by_abbrev),
            annotation_markers=markers,
        )

    # expand == FULL
    patristic_map = await _fetch_patristic_map()
    book_names = await _fetch_book_names([doc["book_id"]])
    books_ordered = await _fetch_books_ordered()

    # Batch resolve cross-refs
    cross_ref_ids = doc.get("cross_ref_targets", [])
    refs_by_id = await _get_passage_refs_batch(cross_ref_ids)
    cross_refs = [refs_by_id[rid] for rid in cross_ref_ids if rid in refs_by_id]

    navigation = await _get_navigation_cross_book(doc, books_ordered)

    html = None
    if include_html:
        html = await _get_html(passage_id)

    minimal = _doc_to_minimal(doc)
    return PassageFull(
        **minimal.model_dump(),
        book_name=book_names.get(doc["book_id"], doc["book_id"]),
        html=html,
        annotations=_group_annotations_full(
            annotations, patristic_map, book_names_by_abbrev
        ),
        annotation_markers=markers,
        cross_references=CrossReferenceData(
            text=doc.get("cross_ref_text"),
            targets=cross_refs,
        ),
        navigation=navigation,
    )


async def get_passages_by_ids(
    passage_ids: list[str],
    expand: ExpandMode = ExpandMode.NONE,
) -> list[PassageMinimal | PassageWithAnnotations | PassageFull]:
    """Batch fetch passages by IDs."""
    db = MongoDB.db_dox

    cursor = db.passages.find({"_id": {"$in": passage_ids}})
    docs = await cursor.to_list(length=None)

    if expand == ExpandMode.NONE:
        return [_doc_to_minimal(d) for d in docs]

    # Fetch book abbreviation mappings for scripture refs
    book_names_by_abbrev = await _fetch_book_names_by_abbrev()

    # Batch fetch all annotations
    all_ann_ids = []
    for doc in docs:
        all_ann_ids.extend(doc.get("study_note_ids", []))
        all_ann_ids.extend(doc.get("liturgical_ids", []))
        all_ann_ids.extend(doc.get("variant_ids", []))
        all_ann_ids.extend(doc.get("citation_ids", []))
        all_ann_ids.extend(doc.get("article_ids", []))

    all_annotations = await _fetch_annotations(list(set(all_ann_ids)))
    ann_by_id = {a["_id"]: a for a in all_annotations}

    patristic_map = {}
    book_names = {}
    refs_by_id = {}

    if expand == ExpandMode.FULL:
        patristic_map = await _fetch_patristic_map()
        book_ids = list({d["book_id"] for d in docs})
        book_names = await _fetch_book_names(book_ids)

        # Batch fetch all cross-ref targets
        all_cross_ref_ids = []
        for doc in docs:
            all_cross_ref_ids.extend(doc.get("cross_ref_targets", []))
        refs_by_id = await _get_passage_refs_batch(all_cross_ref_ids)

    results = []
    for doc in docs:
        doc_ann_ids = (
            doc.get("study_note_ids", [])
            + doc.get("liturgical_ids", [])
            + doc.get("variant_ids", [])
            + doc.get("citation_ids", [])
            + doc.get("article_ids", [])
        )
        doc_annotations = [ann_by_id[aid] for aid in doc_ann_ids if aid in ann_by_id]
        markers = [_doc_to_marker(m) for m in doc.get("annotation_markers", [])]
        minimal = _doc_to_minimal(doc)

        if expand == ExpandMode.ANNOTATIONS:
            results.append(PassageWithAnnotations(
                **minimal.model_dump(),
                annotations=_group_annotations(doc_annotations, book_names_by_abbrev),
                annotation_markers=markers,
            ))
        else:
            # FULL - use batched cross-refs
            cross_ref_ids = doc.get("cross_ref_targets", [])
            cross_refs = [refs_by_id[rid] for rid in cross_ref_ids if rid in refs_by_id]

            results.append(PassageFull(
                **minimal.model_dump(),
                book_name=book_names.get(doc["book_id"], doc["book_id"]),
                html=None,
                annotations=_group_annotations_full(
                    doc_annotations, patristic_map, book_names_by_abbrev
                ),
                annotation_markers=markers,
                cross_references=CrossReferenceData(
                    text=doc.get("cross_ref_text"),
                    targets=cross_refs,
                ),
                navigation=NavigationLinks(prev=None, next=None),
            ))

    return results


async def get_chapter_passages(
    book_id: str,
    chapter: int,
    expand: ExpandMode = ExpandMode.NONE,
    verse_start: int | None = None,
    verse_end: int | None = None,
) -> tuple[list[PassageMinimal | PassageWithAnnotations | PassageFull], ChapterNavigation]:
    """Get all passages in a chapter. Returns (passages, navigation)."""
    db = MongoDB.db_dox

    query = {"book_id": book_id, "chapter": chapter}
    if verse_start is not None:
        query["verse"] = {"$gte": verse_start}
    if verse_end is not None:
        query.setdefault("verse", {})["$lte"] = verse_end

    cursor = db.passages.find(query).sort("verse", 1)
    docs = await cursor.to_list(length=None)

    # Get chapter count and books for navigation
    max_chapter_doc = await db.passages.find_one(
        {"book_id": book_id}, {"chapter": 1}, sort=[("chapter", -1)]
    )
    chapter_count = max_chapter_doc["chapter"] if max_chapter_doc else 1
    books_ordered = await _fetch_books_ordered()

    navigation = await _get_chapter_navigation(
        book_id, chapter, chapter_count, books_ordered
    )

    if not docs:
        return [], navigation

    if expand == ExpandMode.NONE:
        return [_doc_to_minimal(d) for d in docs], navigation

    # Fetch book abbreviation mappings for scripture refs
    book_names_by_abbrev = await _fetch_book_names_by_abbrev()

    # Batch fetch all annotations for the chapter
    all_ann_ids = []
    for doc in docs:
        all_ann_ids.extend(doc.get("study_note_ids", []))
        all_ann_ids.extend(doc.get("liturgical_ids", []))
        all_ann_ids.extend(doc.get("variant_ids", []))
        all_ann_ids.extend(doc.get("citation_ids", []))
        all_ann_ids.extend(doc.get("article_ids", []))

    all_annotations = await _fetch_annotations(list(set(all_ann_ids)))
    ann_by_id = {a["_id"]: a for a in all_annotations}

    patristic_map = {}
    book_names = {}
    refs_by_id = {}

    if expand == ExpandMode.FULL:
        patristic_map = await _fetch_patristic_map()
        book_names = await _fetch_book_names([book_id])

        # Batch fetch all cross-ref targets
        all_cross_ref_ids = []
        for doc in docs:
            all_cross_ref_ids.extend(doc.get("cross_ref_targets", []))
        refs_by_id = await _get_passage_refs_batch(all_cross_ref_ids)

    results = []
    for doc in docs:
        doc_ann_ids = (
            doc.get("study_note_ids", [])
            + doc.get("liturgical_ids", [])
            + doc.get("variant_ids", [])
            + doc.get("citation_ids", [])
            + doc.get("article_ids", [])
        )
        doc_annotations = [ann_by_id[aid] for aid in doc_ann_ids if aid in ann_by_id]
        markers = [_doc_to_marker(m) for m in doc.get("annotation_markers", [])]
        minimal = _doc_to_minimal(doc)

        if expand == ExpandMode.ANNOTATIONS:
            results.append(PassageWithAnnotations(
                **minimal.model_dump(),
                annotations=_group_annotations(doc_annotations, book_names_by_abbrev),
                annotation_markers=markers,
            ))
        else:
            # FULL - use batched cross-refs
            cross_ref_ids = doc.get("cross_ref_targets", [])
            cross_refs = [refs_by_id[rid] for rid in cross_ref_ids if rid in refs_by_id]

            results.append(PassageFull(
                **minimal.model_dump(),
                book_name=book_names.get(book_id, book_id),
                html=None,
                annotations=_group_annotations_full(
                    doc_annotations, patristic_map, book_names_by_abbrev
                ),
                annotation_markers=markers,
                cross_references=CrossReferenceData(
                    text=doc.get("cross_ref_text"),
                    targets=cross_refs,
                ),
                navigation=NavigationLinks(prev=None, next=None),
            ))

    return results, navigation
