"""Chat service - thin wrapper around the chat module.

This module delegates to api.chat for the actual implementation.
Kept for backward compatibility with the router.
"""

from collections.abc import AsyncIterator

from api.chat.agent import (
    cancel_stream as _cancel_stream,
    generate_stream_id as _generate_stream_id,
    process_chat as _process_chat,
    process_chat_stream as _process_chat_stream,
)
from api.models.chat import ChatMessage, ChatResponse, ReadingContext, StreamEvent

__all__ = ["process_chat", "process_chat_stream", "generate_stream_id", "cancel_stream"]


async def process_chat(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
    model: str | None = None,
) -> ChatResponse:
    """Process a chat request with the OSB agent.

    This is the main entry point called by the router.

    Args:
        messages: Conversation history from frontend
        context: Current reading context (OSB passage/chapter or library node)
        model: Model to use (glm, grok, kimi, gemini-flash). Defaults to glm.

    Returns:
        ChatResponse with assistant message and tool calls
    """
    return await _process_chat(messages, context, model)


async def process_chat_stream(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
    stream_id: str | None = None,
    model: str | None = None,
) -> AsyncIterator[StreamEvent]:
    """Process a chat request with streaming response.

    This is the streaming entry point called by the router.

    Args:
        messages: Conversation history from frontend
        context: Current reading context (OSB passage/chapter or library node)
        stream_id: Optional ID for cancellation support
        model: Model to use (glm, grok, kimi, gemini-flash). Defaults to glm.

    Yields:
        StreamEvent objects for SSE transmission
    """
    async for event in _process_chat_stream(messages, context, stream_id, model):
        yield event


def generate_stream_id() -> str:
    """Generate a unique stream ID for cancellation support."""
    return _generate_stream_id()


def cancel_stream(stream_id: str) -> bool:
    """Cancel an active stream.

    Args:
        stream_id: The stream ID to cancel

    Returns:
        True if stream was found and cancelled, False otherwise
    """
    return _cancel_stream(stream_id)
