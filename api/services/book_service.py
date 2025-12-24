"""Book query service."""

from api.db import MongoDB
from api.models.book import (
    BookDetail,
    BookListResponse,
    BookSummary,
    ChapterDetail,
    ChapterSummary,
)
from api.models.common import Testament


async def get_books(testament: Testament | None = None) -> BookListResponse:
    """Get all books, optionally filtered by testament."""
    db = MongoDB.db_dox

    # Build query filter
    query = {}
    if testament:
        query["testament"] = testament.value

    # Get books sorted by canonical order
    books_cursor = db.books.find(query).sort("order", 1)
    books_raw = await books_cursor.to_list(length=None)

    # Get passage counts per book using aggregation
    passage_stats = await db.passages.aggregate([
        {"$group": {
            "_id": "$book_id",
            "passage_count": {"$sum": 1},
            "max_chapter": {"$max": "$chapter"},
        }},
    ]).to_list(length=None)

    stats_by_book = {s["_id"]: s for s in passage_stats}

    books = []
    for book in books_raw:
        stats = stats_by_book.get(book["_id"], {})
        books.append(BookSummary(
            id=book["_id"],
            name=book["name"],
            abbreviation=book.get("abbreviation", book.get("abbreviations", [""])[0]),
            abbreviations=book.get("abbreviations", [book.get("abbreviation", "")]),
            order=book["order"],
            testament=Testament(book["testament"]),
            chapter_count=stats.get("max_chapter", 0),
            passage_count=stats.get("passage_count", 0),
        ))

    return BookListResponse(books=books, total=len(books))


async def get_book(book_id: str) -> BookDetail | None:
    """Get a single book with chapter details."""
    db = MongoDB.db_dox

    book = await db.books.find_one({"_id": book_id})
    if not book:
        return None

    # Get chapter breakdown using aggregation
    chapter_stats = await db.passages.aggregate([
        {"$match": {"book_id": book_id}},
        {"$group": {
            "_id": "$chapter",
            "verse_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(length=None)

    chapters = [
        ChapterSummary(chapter=c["_id"], verse_count=c["verse_count"])
        for c in chapter_stats
    ]

    total_passages = sum(c.verse_count for c in chapters)

    return BookDetail(
        id=book["_id"],
        name=book["name"],
        abbreviation=book.get("abbreviation", book.get("abbreviations", [""])[0]),
        abbreviations=book.get("abbreviations", [book.get("abbreviation", "")]),
        order=book["order"],
        testament=Testament(book["testament"]),
        chapter_count=len(chapters),
        passage_count=total_passages,
        chapters=chapters,
    )


async def get_chapter(book_id: str, chapter: int) -> ChapterDetail | None:
    """Get chapter metadata."""
    db = MongoDB.db_dox

    # Get book name
    book = await db.books.find_one({"_id": book_id}, {"name": 1})
    if not book:
        return None

    # Get passages in this chapter
    passages = await db.passages.find(
        {"book_id": book_id, "chapter": chapter},
        {"_id": 1, "verse": 1},
    ).sort("verse", 1).to_list(length=None)

    if not passages:
        return None

    return ChapterDetail(
        book_id=book_id,
        book_name=book["name"],
        chapter=chapter,
        verse_count=len(passages),
        first_verse_id=passages[0]["_id"],
        last_verse_id=passages[-1]["_id"],
    )
