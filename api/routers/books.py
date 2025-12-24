"""Book endpoints."""

from fastapi import APIRouter, HTTPException

from api.models.book import BookDetail, BookListResponse, ChapterDetail
from api.models.common import ExpandMode, Testament
from api.models.passage import (
    ChapterPassagesResponse,
    PassageFull,
    PassageMinimal,
    PassageWithAnnotations,
)
from api.services import book_service, passage_service

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=BookListResponse)
async def list_books(testament: Testament | None = None):
    """List all books, optionally filtered by testament."""
    return await book_service.get_books(testament)


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: str):
    """Get book details with chapter breakdown."""
    book = await book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book not found: {book_id}")
    return book


@router.get("/{book_id}/chapters/{chapter}", response_model=ChapterDetail)
async def get_chapter(book_id: str, chapter: int):
    """Get chapter metadata."""
    chapter_detail = await book_service.get_chapter(book_id, chapter)
    if not chapter_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter not found: {book_id} chapter {chapter}",
        )
    return chapter_detail


@router.get("/{book_id}/chapters/{chapter}/passages")
async def get_chapter_passages(
    book_id: str,
    chapter: int,
    expand: ExpandMode = ExpandMode.NONE,
    verse_start: int | None = None,
    verse_end: int | None = None,
) -> ChapterPassagesResponse:
    """
    Get all passages in a chapter.

    Optimized for reader component - full chapter fetch with optional annotations.
    Use `verse_start` and `verse_end` to filter to a verse range.

    Includes chapter navigation with cross-book support (Genesis 50 -> Exodus 1).
    """
    # Verify book exists
    book = await book_service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book not found: {book_id}")

    passages, navigation = await passage_service.get_chapter_passages(
        book_id, chapter, expand, verse_start, verse_end
    )

    if not passages:
        raise HTTPException(
            status_code=404,
            detail=f"No passages found: {book_id} chapter {chapter}",
        )

    return ChapterPassagesResponse(
        book_id=book_id,
        book_name=book.name,
        chapter=chapter,
        passages=passages,
        total=len(passages),
        navigation=navigation,
    )
