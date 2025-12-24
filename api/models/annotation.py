"""Annotation and Patristic source Pydantic models."""

from pydantic import BaseModel

from api.models.common import AnnotationType


class AnnotationDetail(BaseModel):
    """Full annotation details."""

    id: str
    type: AnnotationType
    passage_ids: list[str] = []
    verse_display: str
    text: str
    patristic_citations: list[str] = []
    scripture_refs: list[str] = []


class AnnotationListResponse(BaseModel):
    """Paginated annotation list response."""

    annotations: list[AnnotationDetail]
    total: int
    limit: int
    offset: int


class PatristicSource(BaseModel):
    """Patristic source (Church Father)."""

    id: str
    name: str


class PatristicSourceWithCount(PatristicSource):
    """Patristic source with citation count."""

    citation_count: int


class PatristicSourceListResponse(BaseModel):
    """Response for /patristic-sources endpoint."""

    sources: list[PatristicSourceWithCount]
    total: int
