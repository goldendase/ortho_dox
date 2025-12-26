"""Library-related Pydantic models for theological works."""

from enum import Enum

from pydantic import BaseModel, Field

from api.models.common import PaginatedResponse


class WorkCategory(str, Enum):
    """Categories for library works."""

    PATRISTIC = "patristic"
    BIOGRAPHY = "biography"
    CHURCH_HISTORY = "church_history"
    SPIRITUAL = "spiritual"
    LITURGICAL = "liturgical"
    THEOLOGICAL = "theological"


class AuthorRole(str, Enum):
    """Roles an author can have."""

    AUTHOR = "author"
    TRANSLATOR = "translator"
    EDITOR = "editor"
    COMPILER = "compiler"


class ComponentType(str, Enum):
    """Types of components embedded in content."""

    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    IMAGE = "image"
    QUOTE = "quote"
    EPIGRAPH = "epigraph"
    POEM = "poem"
    LETTER = "letter"


class LibraryExpandMode(str, Enum):
    """Expand modes for library node responses."""

    NONE = "none"
    COMPONENTS = "components"
    FULL = "full"


# --- Author Models ---


class AuthorSummary(BaseModel):
    """Brief author info for work listings."""

    id: str
    name: str
    role: AuthorRole


class AuthorDetail(BaseModel):
    """Full author details."""

    id: str
    name: str
    role: AuthorRole = AuthorRole.AUTHOR
    dates: str | None = None
    description: str | None = None


class AuthorWithCount(BaseModel):
    """Author info with work count for author listings."""

    id: str
    name: str
    dates: str | None = None
    work_count: int = 0


class AuthorListResponse(BaseModel):
    """Response for listing authors."""

    authors: list[AuthorWithCount]
    total: int


class AuthorWorksResponse(BaseModel):
    """Response for author's works."""

    author: AuthorSummary
    works: list["WorkSummary"]
    total: int


# --- Component Models ---


class FootnoteComponent(BaseModel):
    """Footnote or endnote component."""

    id: str
    type: ComponentType
    marker: str  # "[a]", "1", etc.
    content: str


class ImageComponent(BaseModel):
    """Image component."""

    id: str
    type: ComponentType = ComponentType.IMAGE
    image_path: str
    caption: str | None = None
    alt_text: str | None = None


class QuoteComponent(BaseModel):
    """Block quote or epigraph component."""

    id: str
    type: ComponentType
    content: str
    attribution: str | None = None


class ComponentsGroup(BaseModel):
    """Grouped components by type."""

    footnotes: list[FootnoteComponent] = []
    endnotes: list[FootnoteComponent] = []
    images: list[ImageComponent] = []
    quotes: list[QuoteComponent] = []
    epigraphs: list[QuoteComponent] = []


# --- Node Models ---


class NodeSummary(BaseModel):
    """Minimal node info for TOC and navigation."""

    id: str
    title: str | None = None
    label: str | None = None  # "Part I", "Chapter 3"
    node_type: str
    is_leaf: bool
    order: float = 0


class NodeTOC(BaseModel):
    """Node info for table of contents (recursive tree)."""

    id: str
    title: str | None = None
    label: str | None = None
    node_type: str
    is_leaf: bool
    order: float = 0
    children: list["NodeTOC"] = []


class NodeNavigation(BaseModel):
    """Navigation links for a node."""

    prev: NodeSummary | None = None
    next: NodeSummary | None = None
    parent: NodeSummary | None = None


class NodeMinimal(BaseModel):
    """Minimal node response (expand=none)."""

    id: str
    work_id: str
    title: str | None = None
    label: str | None = None
    node_type: str
    depth: int
    is_leaf: bool
    content: str | None = None  # Only for leaf nodes
    content_html: str | None = None


class NodeWithComponents(NodeMinimal):
    """Node with resolved components (expand=components)."""

    components: ComponentsGroup = Field(default_factory=ComponentsGroup)
    navigation: NodeNavigation = Field(default_factory=NodeNavigation)


class NodeFull(NodeWithComponents):
    """Full node with all context (expand=full)."""

    work_title: str | None = None
    author: AuthorSummary | None = None
    scripture_refs: list["ScriptureRefTarget"] = []


# --- Work Models ---


class WorkSummary(BaseModel):
    """Brief work info for listings."""

    id: str
    title: str
    subtitle: str | None = None
    authors: list[AuthorSummary] = []
    category: WorkCategory
    subjects: list[str] = []
    node_count: int = 0
    has_images: bool = False


class WorkDetail(BaseModel):
    """Full work details."""

    id: str
    title: str
    subtitle: str | None = None
    authors: list[AuthorDetail] = []
    publisher: str | None = None
    publication_date: str | None = None
    isbn: str | None = None
    category: WorkCategory
    subjects: list[str] = []
    source_format: str | None = None
    node_count: int = 0
    leaf_count: int = 0
    scripture_ref_count: int = 0


class WorkListResponse(PaginatedResponse):
    """Response for listing works."""

    works: list[WorkSummary]


class WorkTOCResponse(BaseModel):
    """Response for work table of contents."""

    work_id: str
    root: NodeTOC


# --- Scripture Reference Models ---


class ScriptureRefTarget(BaseModel):
    """Target OSB passage info for a scripture reference."""

    passage_id: str
    book_id: str
    book_name: str
    chapter: int
    verse_start: int
    verse_end: int | None = None
    preview: str | None = None  # First ~100 chars of passage text


class ScriptureRefDetail(BaseModel):
    """Full scripture reference with source and target info."""

    id: str
    source_node_id: str
    source_node_title: str | None = None
    reference_text: str  # "Matt. 5:3" as written in source
    target: ScriptureRefTarget


class ScriptureRefsResponse(PaginatedResponse):
    """Response for scripture references from a work/node."""

    work_id: str
    work_title: str | None = None
    scripture_refs: list[ScriptureRefDetail]


# --- Library Refs for OSB Integration ---


class LibraryRefAuthor(BaseModel):
    """Minimal author info for library refs."""

    id: str
    name: str


class LibraryRef(BaseModel):
    """Reference from library to OSB passage."""

    work_id: str
    work_title: str
    node_id: str
    node_title: str | None = None
    author: LibraryRefAuthor | None = None
    reference_text: str
    context_snippet: str | None = None  # ~100 chars around the reference


class PassageLibraryRefsResponse(BaseModel):
    """Response for library refs to an OSB passage."""

    passage_id: str
    passage_display: str  # "John 3:16"
    library_refs: list[LibraryRef]
    total: int


# --- Context Models ---


class LibraryContextResponse(BaseModel):
    """Rich context bundle for MCP consumption."""

    node: NodeWithComponents
    author: AuthorDetail | None = None
    scripture_references: list[ScriptureRefTarget] = []
    navigation: NodeNavigation


# Update forward refs
NodeTOC.model_rebuild()
AuthorWorksResponse.model_rebuild()
