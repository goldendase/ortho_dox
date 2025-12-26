"""Conversation history formatting and compaction.

Handles:
- Formatting message history for DSPy signature input
- Token estimation for history length
- Compaction via summarization when history exceeds threshold
"""

import logging

import dspy

from api.models.chat import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

# Token threshold for compaction (approximate)
MAX_HISTORY_TOKENS = 40000
# Keep this many recent message pairs intact when compacting
KEEP_RECENT_PAIRS = 5
# Approximate chars per token (conservative estimate)
CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length.

    This is a rough approximation. For production accuracy,
    use tiktoken with the specific model's tokenizer.
    """
    return int(len(text) / CHARS_PER_TOKEN)


def format_history(messages: list[ChatMessage]) -> str:
    """Format conversation history for DSPy input.

    Args:
        messages: List of chat messages (excluding current question)

    Returns:
        Formatted string with role-labeled turns
    """
    if not messages:
        return "No previous conversation."

    lines = []
    for msg in messages:
        role_label = "User" if msg.role == MessageRole.USER else "Assistant"
        lines.append(f"**{role_label}:** {msg.content}")
        lines.append("")

    return "\n".join(lines).strip()


async def compact_history(
    messages: list[ChatMessage],
    max_tokens: int = MAX_HISTORY_TOKENS,
) -> str:
    """Format and optionally compact conversation history.

    If history exceeds max_tokens, older messages are summarized
    while keeping recent exchanges intact.

    Args:
        messages: List of chat messages (excluding current question)
        max_tokens: Maximum token threshold before compaction

    Returns:
        Formatted history string, possibly with summarized older content
    """
    if not messages:
        return "No previous conversation."

    # First, format full history and check size
    full_history = format_history(messages)
    token_count = estimate_tokens(full_history)

    if token_count <= max_tokens:
        return full_history

    logger.info(f"History exceeds {max_tokens} tokens ({token_count}), compacting...")

    # Split into older messages (to summarize) and recent (to keep)
    keep_count = KEEP_RECENT_PAIRS * 2  # Each pair is user + assistant
    if len(messages) <= keep_count:
        # Not enough messages to split, return as-is
        return full_history

    older_messages = messages[:-keep_count]
    recent_messages = messages[-keep_count:]

    # Summarize older messages
    older_text = format_history(older_messages)
    summary = await _summarize_history(older_text)

    # Combine summary with recent messages
    recent_text = format_history(recent_messages)

    return f"**Earlier conversation summary:**\n{summary}\n\n**Recent conversation:**\n{recent_text}"


async def _summarize_history(history_text: str) -> str:
    """Summarize older conversation history using a fast model.

    Args:
        history_text: Formatted history text to summarize

    Returns:
        Concise summary of the conversation
    """
    try:
        # Use the fast model for summarization
        from api.lm import get_lm

        fast_lm = get_lm("gemini-flash")

        class SummarizeSignature(dspy.Signature):
            """Summarize a conversation history concisely."""
            conversation: str = dspy.InputField(desc="The conversation history to summarize")
            summary: str = dspy.OutputField(desc="A concise summary of the key points discussed")

        summarizer = dspy.Predict(SummarizeSignature)

        with dspy.context(lm=fast_lm):
            result = summarizer(conversation=history_text)

        return result.summary

    except Exception as e:
        logger.warning(f"History summarization failed: {e}, using truncation fallback")
        # Fallback: truncate older history
        max_chars = 2000
        if len(history_text) > max_chars:
            return history_text[:max_chars] + "\n\n[Earlier conversation truncated]"
        return history_text
