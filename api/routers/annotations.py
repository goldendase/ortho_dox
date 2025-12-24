"""Annotation endpoints."""

from fastapi import APIRouter, HTTPException, Query

from api.models.annotation import AnnotationDetail, AnnotationListResponse
from api.models.common import AnnotationType
from api.services import annotation_service

router = APIRouter(prefix="/annotations", tags=["annotations"])


@router.get("", response_model=AnnotationListResponse)
async def list_annotations(
    type: AnnotationType | None = None,
    patristic_source: str | None = Query(
        None, description="Filter by Church Father ID (e.g., 'BasilG')"
    ),
    book_id: str | None = Query(
        None, description="Filter to annotations in a specific book"
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Query annotations with filters.

    - `type`: Filter by annotation type (study, liturgical, variant, citation, article)
    - `patristic_source`: Filter by Church Father ID
    - `book_id`: Filter to annotations linked to passages in a book
    """
    return await annotation_service.get_annotations(
        type=type,
        patristic_source=patristic_source,
        book_id=book_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{annotation_id}", response_model=AnnotationDetail)
async def get_annotation(annotation_id: str):
    """Get a single annotation by ID."""
    annotation = await annotation_service.get_annotation(annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=404, detail=f"Annotation not found: {annotation_id}"
        )
    return annotation
