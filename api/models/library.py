"""Library-related Pydantic models for theological works."""

from enum import Enum

from pydantic import BaseModel, Field

from api.models.common import PaginatedResponse


# --- Enums ---


class Era(str, Enum):
    """Historical eras for library works."""

    APOSTOLIC = "apostolic"      # 1st-2nd century
    NICENE = "nicene"            # 3rd-5th century
    BYZANTINE = "byzantine"      # 6th-15th century
    EARLY_MODERN = "early_modern"  # 16th-19th century
    MODERN = "modern"            # 20th century+


class Tradition(str, Enum):
    """Religious tradition of the work."""

    EASTERN_ORTHODOX = "eastern_orthodox"
    ORIENTAL_ORTHODOX = "oriental_orthodox"
    CATHOLIC = "catholic"
    PROTESTANT = "protestant"
    ECUMENICAL = "ecumenical"
    HERETICAL = "heretical"


class WorkType(str, Enum):
    """Types of library works."""

    COMMENTARY = "commentary"    # Scripture exegesis (verse-by-verse, book-by-book)
    ASCETICAL = "ascetical"      # Prayer, spiritual practice, inner life
    PASTORAL = "pastoral"        # Letters, practical guidance, formation
    DOCTRINAL = "doctrinal"      # Theological teaching, topical homilies
    HISTORICAL = "historical"    # Lives of saints, biographies, church history


class ReadingLevel(str, Enum):
    """Reading difficulty level."""

    INQUIRER = "inquirer"        # Accessible to newcomers
    CATECHUMEN = "catechumen"    # Some familiarity helpful
    FAITHFUL = "faithful"        # Assumes basic Orthodox knowledge
    SCHOLAR = "scholar"          # Academic, dense


class ContributorRole(str, Enum):
    """Roles a contributor can have."""

    TRANSLATOR = "translator"
    EDITOR = "editor"
    COMPILER = "compiler"
    CONTRIBUTOR = "contributor"  # Catch-all for forewords, introductions, etc.


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


# --- Contributor Model ---


class Contributor(BaseModel):
    """Contributor to a work (translator, editor, compiler)."""

    name: str
    role: ContributorRole


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


class NodeWithComponents(NodeMinimal):
    """Node with resolved components (expand=components)."""

    components: ComponentsGroup = Field(default_factory=ComponentsGroup)
    navigation: NodeNavigation = Field(default_factory=NodeNavigation)


class NodeFull(NodeWithComponents):
    """Full node with all context (expand=full)."""

    work_title: str | None = None
    author: str | None = None  # Resolved author display name
    scripture_refs: list["ScriptureRefTarget"] = []


# --- Work Models ---


class WorkSummary(BaseModel):
    """Brief work info for listings."""

    id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    notes: str | None = None  # Edition/translation caveats
    author: str  # Resolved display name
    contributors: list[Contributor] = []
    work_type: WorkType
    era: Era
    reading_level: ReadingLevel
    tags: list[str] = []
    node_count: int = 0
    has_images: bool = False


class WorkDetail(BaseModel):
    """Full work details."""

    id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    relevance: str | None = None
    notes: str | None = None
    author: str  # Resolved display name
    contributors: list[Contributor] = []
    work_type: WorkType
    era: Era
    tradition: Tradition
    reading_level: ReadingLevel
    tags: list[str] = []
    cover_image: str | None = None
    publication_year: int | None = None
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


# --- Filter Models ---


class FilterAuthor(BaseModel):
    """Author info for filter dropdown."""

    name: str
    work_count: int


class FiltersResponse(BaseModel):
    """Available filter values for the library index."""

    authors: list[FilterAuthor]
    work_types: list[str]
    eras: list[str]
    reading_levels: list[str]


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


class LibraryRef(BaseModel):
    """Reference from library to OSB passage."""

    work_id: str
    work_title: str
    node_id: str
    node_title: str | None = None
    author: str | None = None  # Resolved display name
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
    author: str | None = None  # Resolved display name
    scripture_references: list[ScriptureRefTarget] = []
    navigation: NodeNavigation


# Update forward refs
NodeTOC.model_rebuild()
