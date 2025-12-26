"""Library endpoints for theological works."""

from fastapi import APIRouter, HTTPException, Query

from api.models.library import (
    AuthorDetail,
    AuthorListResponse,
    AuthorRole,
    AuthorWorksResponse,
    LibraryContextResponse,
    LibraryExpandMode,
    NodeFull,
    NodeMinimal,
    NodeWithComponents,
    ScriptureRefsResponse,
    WorkCategory,
    WorkDetail,
    WorkListResponse,
    WorkTOCResponse,
)
from api.services import library_service

router = APIRouter(prefix="/library", tags=["library"])


# --- Works ---


@router.get("/works", response_model=WorkListResponse)
async def list_works(
    category: WorkCategory | None = None,
    author: str | None = Query(None, description="Filter by author ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all theological works in the library.

    Filter by category (patristic, biography, etc.) or author.
    """
    return await library_service.get_works(category, author, limit, offset)


@router.get("/works/{work_id}", response_model=WorkDetail)
async def get_work(work_id: str):
    """
    Get full details for a work.

    Includes author info, publication details, and content statistics.
    """
    work = await library_service.get_work(work_id)
    if not work:
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")
    return work


@router.get("/works/{work_id}/toc", response_model=WorkTOCResponse)
async def get_work_toc(work_id: str):
    """
    Get table of contents for a work.

    Returns the full node tree structure WITHOUT leaf content.
    Use this for rendering navigation UI, sidebars, and book indexes.
    """
    toc = await library_service.get_work_toc(work_id)
    if not toc:
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")
    return toc


# --- Nodes ---


@router.get("/works/{work_id}/nodes/{node_id}")
async def get_node(
    work_id: str,
    node_id: str,
    expand: LibraryExpandMode = LibraryExpandMode.NONE,
):
    """
    Get a specific node (chapter/section) from a work.

    Expand modes:
    - `none`: Node metadata only
    - `components`: Include resolved footnotes, images, quotes
    - `full`: Include scripture refs, author info, full navigation
    """
    node = await library_service.get_node(work_id, node_id, expand)
    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {node_id} in work {work_id}",
        )
    # Return dict to avoid Union type serialization issues with Pydantic v2
    return node.model_dump()


# --- Scripture References ---


@router.get("/works/{work_id}/scripture-refs", response_model=ScriptureRefsResponse)
async def get_work_scripture_refs(
    work_id: str,
    book: str | None = Query(None, description="Filter by OSB book (e.g., 'matthew')"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get all scripture references from a work.

    Returns references to OSB passages with preview text.
    Filter by target book to find references to specific biblical books.
    """
    refs = await library_service.get_work_scripture_refs(work_id, book, limit, offset)
    if not refs:
        raise HTTPException(status_code=404, detail=f"Work not found: {work_id}")
    return refs


@router.get(
    "/works/{work_id}/nodes/{node_id}/scripture-refs",
    response_model=ScriptureRefsResponse,
)
async def get_node_scripture_refs(work_id: str, node_id: str):
    """
    Get scripture references from a specific node.

    Returns only references within the specified chapter/section.
    """
    refs = await library_service.get_node_scripture_refs(work_id, node_id)
    if not refs:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {node_id} in work {work_id}",
        )
    return refs


# --- Authors ---


@router.get("/authors", response_model=AuthorListResponse)
async def list_authors(
    role: AuthorRole | None = Query(None, description="Filter by role"),
):
    """
    List all authors in the library.

    Returns authors aggregated from all works with work counts.
    """
    return await library_service.get_authors(role)


@router.get("/authors/{author_id}", response_model=AuthorDetail)
async def get_author(author_id: str):
    """Get details for a specific author."""
    author = await library_service.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail=f"Author not found: {author_id}")
    return author


@router.get("/authors/{author_id}/works", response_model=AuthorWorksResponse)
async def get_author_works(author_id: str):
    """Get all works by an author."""
    result = await library_service.get_author_works(author_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Author not found: {author_id}")
    return result


# --- Context (MCP) ---


@router.get("/context/{work_id}/{node_id}", response_model=LibraryContextResponse)
async def get_library_context(work_id: str, node_id: str):
    """
    Get rich context bundle for MCP/LLM consumption.

    Includes:
    - Node content with resolved components
    - Author information
    - Scripture references with OSB previews
    - Navigation links
    """
    context = await library_service.get_library_context(work_id, node_id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail=f"Node not found: {node_id} in work {work_id}",
        )
    return context
