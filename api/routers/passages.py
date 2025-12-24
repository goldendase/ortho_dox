"""Passage endpoints."""

from fastapi import APIRouter, HTTPException, Query

from api.models.common import ExpandMode
from api.models.passage import (
    PassageFull,
    PassageMinimal,
    PassageWithAnnotations,
)
from api.services import passage_service

router = APIRouter(prefix="/passages", tags=["passages"])


@router.get("/{passage_id}")
async def get_passage(
    passage_id: str,
    expand: ExpandMode = ExpandMode.NONE,
    include_html: bool = False,
) -> PassageMinimal | PassageWithAnnotations | PassageFull:
    """
    Get a single passage by ID.

    Expand modes:
    - `none`: Minimal response with annotation IDs only
    - `annotations`: Embedded annotations grouped by type
    - `full`: Full context with cross-refs, navigation, patristic names
    """
    passage = await passage_service.get_passage(passage_id, expand, include_html)
    if not passage:
        raise HTTPException(status_code=404, detail=f"Passage not found: {passage_id}")
    return passage


@router.get("")
async def get_passages(
    ids: str = Query(..., description="Comma-separated passage IDs"),
    expand: ExpandMode = ExpandMode.NONE,
) -> list[PassageMinimal | PassageWithAnnotations | PassageFull]:
    """
    Batch fetch passages by IDs.

    Example: `/passages?ids=Gen_vchap1-1,Gen_vchap1-2,Gen_vchap1-3`
    """
    passage_ids = [pid.strip() for pid in ids.split(",") if pid.strip()]
    if not passage_ids:
        raise HTTPException(status_code=400, detail="No passage IDs provided")
    if len(passage_ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 passages per request")

    return await passage_service.get_passages_by_ids(passage_ids, expand)
