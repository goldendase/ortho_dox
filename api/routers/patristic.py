"""Patristic source endpoints."""

from fastapi import APIRouter, HTTPException, Query

from api.models.annotation import (
    AnnotationListResponse,
    PatristicSource,
    PatristicSourceListResponse,
)
from api.services import annotation_service

router = APIRouter(prefix="/patristic-sources", tags=["patristic"])


@router.get("", response_model=PatristicSourceListResponse)
async def list_patristic_sources():
    """
    List all patristic sources (Church Fathers) with citation counts.

    Results are sorted by citation count descending.
    """
    return await annotation_service.get_patristic_sources()


@router.get("/{source_id}", response_model=PatristicSource)
async def get_patristic_source(source_id: str):
    """Get a single patristic source by ID."""
    source = await annotation_service.get_patristic_source(source_id)
    if not source:
        raise HTTPException(
            status_code=404, detail=f"Patristic source not found: {source_id}"
        )
    return source


@router.get("/{source_id}/annotations", response_model=AnnotationListResponse)
async def get_source_annotations(
    source_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all annotations citing a specific Church Father."""
    # Verify source exists
    source = await annotation_service.get_patristic_source(source_id)
    if not source:
        raise HTTPException(
            status_code=404, detail=f"Patristic source not found: {source_id}"
        )

    return await annotation_service.get_annotations_by_patristic_source(
        source_id, limit=limit, offset=offset
    )
