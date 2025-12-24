"""Context-related Pydantic models for MCP consumption."""

from pydantic import BaseModel

from api.models.annotation import AnnotationDetail
from api.models.passage import PassageFull, PassageRef, PatristicCitationExpanded


class CrossReferences(BaseModel):
    """Bidirectional cross-references for a passage."""

    outgoing: list[PassageRef] = []  # Passages this verse references
    incoming: list[PassageRef] = []  # Passages that reference this verse


class PassageContext(BaseModel):
    """Full context bundle for a passage (MCP-focused)."""

    passage: PassageFull
    cross_references: CrossReferences
    patristic_sources: list[PatristicCitationExpanded] = []
    related_articles: list[AnnotationDetail] = []


class CrossRefsResponse(BaseModel):
    """Response for cross-refs only endpoint."""

    passage_id: str
    outgoing: list[PassageRef] = []
    incoming: list[PassageRef] = []
