"""Chat request and response models."""

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Discriminator, Field, Tag


class MessageRole(str, Enum):
    """Chat message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single chat message."""

    role: MessageRole
    content: str


class ToolCall(BaseModel):
    """A tool call made by the agent."""

    name: str
    arguments: dict[str, Any]
    result: Any | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Context Items (multi-item context support)
# ─────────────────────────────────────────────────────────────────────────────


class VerseContextItem(BaseModel):
    """A single verse selection."""

    type: Literal["verse"]
    passage_id: str
    book_id: str
    book_name: str
    chapter: int
    verse: int
    text: str


class VerseRangeContextItem(BaseModel):
    """A verse range selection."""

    type: Literal["verse-range"]
    book_id: str
    book_name: str
    chapter: int
    verse_start: int
    verse_end: int
    passage_ids: list[str]
    text: str


class ParagraphContextItem(BaseModel):
    """A library paragraph selection."""

    type: Literal["paragraph"]
    work_id: str
    work_title: str
    node_id: str
    node_title: str
    paragraph_index: int
    text: str


class OsbNoteContextItem(BaseModel):
    """An OSB annotation (study/liturgical/variant note)."""

    type: Literal["osb-note"]
    note_type: Literal["study", "liturgical", "variant"]
    note_id: str
    verse_display: str
    text: str


class OsbArticleContextItem(BaseModel):
    """An OSB article."""

    type: Literal["osb-article"]
    article_id: str
    text: str


class LibraryFootnoteContextItem(BaseModel):
    """A library footnote/endnote."""

    type: Literal["library-footnote"]
    footnote_id: str
    footnote_type: Literal["footnote", "endnote"]
    marker: str
    text: str


# Discriminated union based on 'type' field
ContextItem = Annotated[
    Union[
        VerseContextItem,
        VerseRangeContextItem,
        ParagraphContextItem,
        OsbNoteContextItem,
        OsbArticleContextItem,
        LibraryFootnoteContextItem,
    ],
    Discriminator("type"),
]


class ReadingContext(BaseModel):
    """Current reading context - OSB (Scripture) or Library (theological works).

    Supports two patterns:
    1. Multi-item context: context_items array with specific selections (verses, paragraphs, notes)
    2. Fallback context: just current reading position (book/chapter or work/node)

    The frontend should send explicit titles/names along with IDs so the agent
    doesn't waste tool calls looking up things the frontend already knows.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-item Context (explicit selections from reading)
    # ─────────────────────────────────────────────────────────────────────────

    context_items: list[ContextItem] | None = Field(
        default=None,
        description="Array of selected context items (verses, paragraphs, notes, etc.).",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback: OSB (Orthodox Study Bible / Scripture) Context
    # Used when no specific items are selected, just reading position
    # ─────────────────────────────────────────────────────────────────────────

    # OSB IDs
    passage_id: str | None = Field(
        default=None,
        description="OSB: Specific verse ID (e.g., 'Gen_vchap1-1').",
    )
    book_id: str | None = Field(
        default=None,
        description="OSB: Book ID (e.g., 'genesis', 'matthew').",
    )
    chapter: int | None = Field(
        default=None,
        description="OSB: Chapter number.",
    )
    verse: int | None = Field(
        default=None,
        description="OSB: Verse number if a specific verse is selected.",
    )

    # OSB explicit content (avoid agent lookups)
    book_name: str | None = Field(
        default=None,
        description="OSB: Human-readable book name (e.g., 'Genesis', 'Matthew').",
    )
    verse_text: str | None = Field(
        default=None,
        description="OSB: The actual verse text if a specific verse is selected.",
    )
    chapter_text: str | None = Field(
        default=None,
        description="OSB: Full chapter text when reading a chapter (no verse selected).",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Library (Theological Works) Context
    # ─────────────────────────────────────────────────────────────────────────

    # Library IDs
    work_id: str | None = Field(
        default=None,
        description="Library: Work ID (e.g., 'on-acquisition-holy-spirit').",
    )
    node_id: str | None = Field(
        default=None,
        description="Library: Section/chapter node ID within the work.",
    )

    # Library explicit content (avoid agent lookups)
    work_title: str | None = Field(
        default=None,
        description="Library: Human-readable work title.",
    )
    node_title: str | None = Field(
        default=None,
        description="Library: Human-readable section/chapter title.",
    )
    node_content: str | None = Field(
        default=None,
        description="Library: Full text content of the current node/section.",
    )
    paragraph_text: str | None = Field(
        default=None,
        description="Library: Text of a selected paragraph within the node (if user selected one).",
    )


class ChatRequest(BaseModel):
    """Chat completion request from frontend."""

    messages: list[ChatMessage] = Field(
        ...,
        description="Conversation history. Frontend manages this list.",
        min_length=1,
    )
    context: ReadingContext | None = Field(
        default=None,
        description="Current reading context - passage or chapter the user is viewing.",
    )


class ChatResponse(BaseModel):
    """Chat completion response."""

    message: ChatMessage = Field(
        ...,
        description="The assistant's response message.",
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list,
        description="Tools called during this turn (for debugging/transparency).",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the request failed.",
    )
