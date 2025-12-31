"""Chat service - thin wrapper around the chat module.

This module delegates to api.chat for the actual implementation.
Kept for backward compatibility with the router.
"""

from collections.abc import AsyncIterator

from api.chat.agent import process_chat as _process_chat, process_chat_stream as _process_chat_stream
from api.models.chat import ChatMessage, ChatResponse, ReadingContext, StreamEvent

__all__ = ["process_chat", "process_chat_stream"]


async def process_chat(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
) -> ChatResponse:
    """Process a chat request with the OSB agent.

    This is the main entry point called by the router.

    Args:
        messages: Conversation history from frontend
        context: Current reading context (OSB passage/chapter or library node)

    Returns:
        ChatResponse with assistant message and tool calls
    """
    return await _process_chat(messages, context)


async def process_chat_stream(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
) -> AsyncIterator[StreamEvent]:
    """Process a chat request with streaming response.

    This is the streaming entry point called by the router.

    Args:
        messages: Conversation history from frontend
        context: Current reading context (OSB passage/chapter or library node)

    Yields:
        StreamEvent objects for SSE transmission
    """
    async for event in _process_chat_stream(messages, context):
        yield event
