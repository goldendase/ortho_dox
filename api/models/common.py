"""Shared enums and types for API models."""

from enum import Enum

from pydantic import BaseModel


class Testament(str, Enum):
    """Old or New Testament."""

    OLD = "old"
    NEW = "new"


class Format(str, Enum):
    """Passage format type."""

    PROSE = "prose"
    POETRY = "poetry"


class AnnotationType(str, Enum):
    """Types of annotations."""

    STUDY = "study"
    LITURGICAL = "liturgical"
    VARIANT = "variant"
    CITATION = "citation"
    ARTICLE = "article"
    CROSS_REF = "cross_ref"  # Cross-reference markers in text


class ExpandMode(str, Enum):
    """Expand modes for passage responses."""

    NONE = "none"
    ANNOTATIONS = "annotations"
    FULL = "full"


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    limit: int = 100
    offset: int = 0


class PaginatedResponse(BaseModel):
    """Base for paginated responses."""

    total: int
    limit: int
    offset: int
