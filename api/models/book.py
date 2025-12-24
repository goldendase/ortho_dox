"""Book-related Pydantic models."""

from pydantic import BaseModel

from api.models.common import Testament


class ChapterSummary(BaseModel):
    """Chapter info within a book."""

    chapter: int
    verse_count: int


class BookSummary(BaseModel):
    """Book summary for list responses."""

    id: str
    name: str
    abbreviation: str
    abbreviations: list[str]
    order: float  # Some books have fractional order (e.g., 49.1 for inserted books)
    testament: Testament
    chapter_count: int
    passage_count: int


class BookDetail(BookSummary):
    """Full book details with chapter breakdown."""

    chapters: list[ChapterSummary]


class ChapterDetail(BaseModel):
    """Chapter metadata."""

    book_id: str
    book_name: str
    chapter: int
    verse_count: int
    first_verse_id: str
    last_verse_id: str


class BookListResponse(BaseModel):
    """Response for /books endpoint."""

    books: list[BookSummary]
    total: int
