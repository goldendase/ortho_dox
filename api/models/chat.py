"""Chat request and response models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class ReadingContext(BaseModel):
    """Current reading context - either a specific passage or a chapter."""

    passage_id: str | None = Field(
        default=None,
        description="Specific passage ID if user has selected a verse.",
    )
    book_id: str | None = Field(
        default=None,
        description="Book ID if reading a chapter (e.g., 'genesis', 'matthew').",
    )
    chapter: int | None = Field(
        default=None,
        description="Chapter number if reading a chapter.",
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
