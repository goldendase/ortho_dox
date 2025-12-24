"""Passage-related Pydantic models for different expand modes."""

from pydantic import BaseModel

from api.models.common import AnnotationType, Format


class AnnotationMarker(BaseModel):
    """Position marker for an annotation in verse text."""

    id: str  # "f1", "fx1", "fvar1", etc.
    type: AnnotationType
    preceding: str  # ~40 chars before marker for positioning


class PassageMinimal(BaseModel):
    """Minimal passage response (expand=none)."""

    id: str  # "Gen_vchap1-1"
    book_id: str
    chapter: int
    verse: int
    text: str  # Preserves <i>/<b> semantic markup
    format: Format
    study_note_ids: list[str] = []
    liturgical_ids: list[str] = []
    variant_ids: list[str] = []
    citation_ids: list[str] = []
    article_ids: list[str] = []
    cross_ref_targets: list[str] = []


class ScriptureRefDisplay(BaseModel):
    """Scripture reference with display string."""

    id: str  # "P2et_vchap2-6"
    display: str  # "2 Peter 2:6"


class AnnotationEmbed(BaseModel):
    """Embedded annotation in passage response."""

    id: str
    type: AnnotationType
    verse_display: str
    text: str
    patristic_citations: list[str] = []  # IDs for annotations mode
    scripture_refs: list[ScriptureRefDisplay] = []


class AnnotationsGroup(BaseModel):
    """Grouped annotations by type."""

    study_notes: list[AnnotationEmbed] = []
    liturgical: list[AnnotationEmbed] = []
    variants: list[AnnotationEmbed] = []
    citations: list[AnnotationEmbed] = []
    articles: list[AnnotationEmbed] = []


class PassageWithAnnotations(PassageMinimal):
    """Passage with embedded annotations (expand=annotations)."""

    annotations: AnnotationsGroup
    annotation_markers: list[AnnotationMarker] = []


class PassageRef(BaseModel):
    """Brief reference to another passage (for cross-refs)."""

    id: str
    book_id: str
    book_name: str
    chapter: int
    verse: int
    preview: str  # First ~100 chars


class PatristicCitationExpanded(BaseModel):
    """Expanded patristic citation with full name."""

    id: str
    name: str


class AnnotationEmbedFull(BaseModel):
    """Embedded annotation with expanded patristic citations (expand=full)."""

    id: str
    type: AnnotationType
    verse_display: str
    text: str
    patristic_citations: list[PatristicCitationExpanded] = []
    scripture_refs: list[ScriptureRefDisplay] = []


class AnnotationsGroupFull(BaseModel):
    """Grouped annotations with expanded patristic citations."""

    study_notes: list[AnnotationEmbedFull] = []
    liturgical: list[AnnotationEmbedFull] = []
    variants: list[AnnotationEmbedFull] = []
    citations: list[AnnotationEmbedFull] = []
    articles: list[AnnotationEmbedFull] = []


class CrossReferenceData(BaseModel):
    """Cross-reference information."""

    text: str | None  # Full cross-ref text from passage
    targets: list[PassageRef] = []


class NavigationLinks(BaseModel):
    """Navigation to adjacent passages."""

    prev: str | None
    next: str | None


class PassageFull(PassageMinimal):
    """Full passage with all context (expand=full)."""

    book_name: str
    html: str | None = None
    annotations: AnnotationsGroupFull
    annotation_markers: list[AnnotationMarker] = []
    cross_references: CrossReferenceData
    navigation: NavigationLinks


class ChapterNavigation(BaseModel):
    """Navigation links to adjacent chapters."""

    prev_chapter: str | None  # "/books/genesis/chapters/49/passages"
    next_chapter: str | None  # "/books/exodus/chapters/1/passages"


class ChapterPassagesResponse(BaseModel):
    """Response for chapter passages endpoint."""

    book_id: str
    book_name: str
    chapter: int
    passages: list[PassageMinimal | PassageWithAnnotations | PassageFull]
    total: int
    navigation: ChapterNavigation
