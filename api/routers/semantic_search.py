"""Semantic search router for vector search across OSB and Library content."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from api.services.vector_search_service import (
    search_osb,
    search_library,
    OSBSearchResult,
    LibrarySearchResult,
)

router = APIRouter(prefix="/semantic-search", tags=["semantic-search"])


# ─────────────────────────────────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────────────────────────────────


class OSBResultModel(BaseModel):
    """A single OSB search result."""
    source_type: str = Field(description="osb_study, osb_article, or osb_chapter")
    score: float = Field(description="Similarity score (0-1)")
    text: str = Field(description="The matched text content")
    annotation_id: Optional[str] = Field(default=None, description="Annotation ID for study notes/articles")
    book_id: Optional[str] = Field(default=None, description="Book ID (e.g., 'genesis')")
    book_name: Optional[str] = Field(default=None, description="Book display name")
    chapter: Optional[int] = Field(default=None, description="Chapter number")
    verse_start: Optional[int] = Field(default=None, description="Starting verse")
    verse_end: Optional[int] = Field(default=None, description="Ending verse")
    passage_ids: Optional[list[str]] = Field(default=None, description="Related passage IDs")


class LibraryResultModel(BaseModel):
    """A single library search result."""
    score: float = Field(description="Similarity score (0-1)")
    text: str = Field(description="The matched text content")
    work_id: str = Field(description="Work ID")
    node_id: str = Field(description="Node ID within the work")
    node_title: Optional[str] = Field(default=None, description="Node title")
    author_id: Optional[str] = Field(default=None, description="Author ID")
    work_title: Optional[str] = Field(default=None, description="Work title")
    author_name: Optional[str] = Field(default=None, description="Author display name")
    chunk_sequence: Optional[int] = Field(default=None, description="Chunk sequence in node")
    scripture_refs: Optional[list[str]] = Field(default=None, description="Scripture references in text")


class OSBSearchResponse(BaseModel):
    """Response for OSB semantic search."""
    results: list[OSBResultModel]
    query: str
    total: int


class LibrarySearchResponse(BaseModel):
    """Response for library semantic search."""
    results: list[LibraryResultModel]
    query: str
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/osb", response_model=OSBSearchResponse)
async def semantic_search_osb(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=20, description="Max results (1-20)"),
    source_type: Optional[str] = Query(
        default=None,
        description="Filter by source type: osb_study, osb_article, osb_chapter"
    ),
) -> OSBSearchResponse:
    """
    Semantic search across OSB content.

    Searches study notes, topical articles, and chapter text using vector similarity.
    Results are ranked by relevance and filtered by a minimum score threshold.
    """
    results = await search_osb(
        query=q,
        top_k=limit,
        source_type_filter=source_type,
    )

    return OSBSearchResponse(
        results=[
            OSBResultModel(
                source_type=r.source_type,
                score=r.score,
                text=r.text,
                annotation_id=r.annotation_id,
                book_id=r.book_id,
                book_name=r.book_name,
                chapter=r.chapter,
                verse_start=r.verse_start,
                verse_end=r.verse_end,
                passage_ids=r.passage_ids,
            )
            for r in results
        ],
        query=q,
        total=len(results),
    )


@router.get("/library", response_model=LibrarySearchResponse)
async def semantic_search_library(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=20, description="Max results (1-20)"),
    author: Optional[str] = Query(default=None, description="Filter by author ID"),
    work: Optional[str] = Query(default=None, description="Filter by work ID"),
) -> LibrarySearchResponse:
    """
    Semantic search across library content.

    Searches patristic texts, biographies, and spiritual writings using vector similarity.
    Results are ranked by relevance and filtered by a minimum score threshold.
    """
    results = await search_library(
        query=q,
        top_k=limit,
        author_filter=author,
        work_filter=work,
    )

    return LibrarySearchResponse(
        results=[
            LibraryResultModel(
                score=r.score,
                text=r.text,
                work_id=r.work_id,
                node_id=r.node_id,
                node_title=r.node_title,
                author_id=r.author_id,
                work_title=r.work_title,
                author_name=r.author_name,
                chunk_sequence=r.chunk_sequence,
                scripture_refs=r.scripture_refs,
            )
            for r in results
        ],
        query=q,
        total=len(results),
    )
