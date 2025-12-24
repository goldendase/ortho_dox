"""Context endpoints for MCP consumption."""

from fastapi import APIRouter, HTTPException

from api.models.context import CrossRefsResponse, PassageContext
from api.services import context_service

router = APIRouter(prefix="/context", tags=["context"])


@router.get("/cross-refs/{passage_id}", response_model=CrossRefsResponse)
async def get_cross_refs(passage_id: str):
    """
    Get bidirectional cross-references for a passage.

    Returns both:
    - **outgoing**: Passages this verse references
    - **incoming**: Passages that reference this verse

    This is the key feature for MCP - discovering related passages in both directions.
    """
    result = await context_service.get_cross_refs(passage_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Passage not found: {passage_id}")
    return result


@router.get("/{passage_id}", response_model=PassageContext)
async def get_passage_context(passage_id: str):
    """
    Get full context bundle for a passage.

    This endpoint is optimized for MCP/LLM consumption, providing everything
    needed to understand a passage in context:

    - **passage**: Full passage with all annotations expanded
    - **cross_references**: Bidirectional refs (outgoing + incoming)
    - **patristic_sources**: Church Fathers cited in annotations
    - **related_articles**: Topical articles linked to this passage
    """
    result = await context_service.get_passage_context(passage_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Passage not found: {passage_id}")
    return result
