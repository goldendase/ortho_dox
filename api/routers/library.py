"""Library endpoints for theological works."""

from fastapi import APIRouter, HTTPException, Query

from api.models.library import (
    Era,
    FiltersResponse,
    LibraryContextResponse,
    LibraryExpandMode,
    ReadingLevel,
    ScriptureRefsResponse,
    WorkDetail,
    WorkListResponse,
    WorkTOCResponse,
    WorkType,
)
from api.services import library_service

router = APIRouter(prefix="/library", tags=["library"])


# --- Works ---


@router.get("/works", response_model=WorkListResponse)
async def list_works(
    work_type: WorkType | None = Query(None, description="Filter by work type"),
    era: Era | None = Query(None, description="Filter by era"),
    reading_level: ReadingLevel | None = Query(None, description="Filter by reading level"),
    author: str | None = Query(None, description="Filter by author name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all theological works in the library.

    Filter by work type, era, reading level, or author name.
    """
    return await library_service.get_works(
        work_type=work_type,
        era=era,
        reading_level=reading_level,
        author=author,
        limit=limit,
        offset=offset,
    )


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


# --- Filters ---


@router.get("/filters", response_model=FiltersResponse)
async def get_filters():
    """
    Get available filter values for the library index.

    Returns lists of authors, work types, eras, and reading levels
    that have at least one work in the library.
    """
    return await library_service.get_filters()


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
