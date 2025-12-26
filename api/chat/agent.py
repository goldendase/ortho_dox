"""OSB Chat Agent using DSPy ReAct.

This module implements the chat agent using DSPy's ReAct pattern with native
tool calling. The agent has access to tools for querying Scripture, study notes,
patristic commentary, and the theological library.
"""

import json
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable

import dspy

from api.chat.context_builder import build_context
from api.chat.history import compact_history
from api.chat.tools import TOOLS as RAW_TOOLS
from api.models.chat import ChatMessage, ChatResponse, MessageRole, ReadingContext, ToolCall

logger = logging.getLogger(__name__)

# =============================================================================
# Chat Logger Setup - Comprehensive LLM logging to ../log/chat.log
# =============================================================================

LOG_DIR = Path(__file__).parent.parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)
CHAT_LOG_FILE = LOG_DIR / "chat.log"

# Create dedicated chat logger
chat_logger = logging.getLogger("api.chat.llm")
chat_logger.setLevel(logging.DEBUG)
chat_logger.propagate = False  # Don't propagate to root logger

# File handler with detailed formatting
_chat_handler = logging.FileHandler(CHAT_LOG_FILE, encoding="utf-8")
_chat_handler.setLevel(logging.DEBUG)
_chat_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
chat_logger.addHandler(_chat_handler)


def _log_separator(title: str):
    """Log a visual separator with title."""
    chat_logger.debug("")
    chat_logger.debug("=" * 80)
    chat_logger.debug(f"  {title}")
    chat_logger.debug("=" * 80)


def _log_section(title: str, content: str, max_len: int = 0):
    """Log a section with title and content."""
    chat_logger.debug("")
    chat_logger.debug(f"--- {title} ---")
    if max_len and len(content) > max_len:
        chat_logger.debug(content[:max_len])
        chat_logger.debug(f"... [{len(content) - max_len} more chars truncated]")
    else:
        chat_logger.debug(content)


# =============================================================================
# Tool Wrapper for Logging
# =============================================================================

def _wrap_tool_with_logging(tool: dspy.Tool) -> dspy.Tool:
    """Wrap a tool's function to log inputs and outputs."""
    original_func = tool.func

    @wraps(original_func)
    async def logged_func(*args, **kwargs):
        # Log tool invocation
        chat_logger.debug("")
        chat_logger.debug(f">>> TOOL CALL: {tool.name}")
        chat_logger.debug(f"    Arguments: {json.dumps(kwargs, default=str)}")

        try:
            result = await original_func(*args, **kwargs)

            # Log result (truncate if very long)
            result_str = str(result)
            if len(result_str) > 2000:
                chat_logger.debug(f"    Result: {result_str[:2000]}")
                chat_logger.debug(f"    ... [{len(result_str) - 2000} more chars]")
            else:
                chat_logger.debug(f"    Result: {result_str}")

            return result

        except Exception as e:
            chat_logger.debug(f"    ERROR: {e}")
            raise

    # Create new tool with logged function
    return dspy.Tool(
        func=logged_func,
        name=tool.name,
        desc=tool.desc,
    )


# Wrap all tools with logging
TOOLS = [_wrap_tool_with_logging(tool) for tool in RAW_TOOLS]


# =============================================================================
# Load System Prompt
# =============================================================================

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "osb_agent_system_prompt.md").read_text()

# Agent configuration
MAX_RETRIES = 3
MAX_TOOL_ITERATIONS = 5


# =============================================================================
# DSPy Signature
# =============================================================================

class OSBSignature(dspy.Signature):
    """Orthodox Study Bible chat assistant with tool access."""

    # Each field becomes a ## section in the prompt
    system: str = dspy.InputField(desc="Your identity, voice, and theological guidelines")
    reading_context: str = dspy.InputField(
        desc="What the user is currently viewing (verse, chapter, or library node) with available resources"
    )
    conversation: str = dspy.InputField(desc="Previous conversation turns")
    question: str = dspy.InputField(desc="The user's current question")
    answer: str = dspy.OutputField(desc="Your response to the user")


# =============================================================================
# OSB Agent
# =============================================================================

class OSBAgent:
    """Orthodox Study Bible chat agent.

    Uses DSPy ReAct to handle conversations about Scripture,
    automatically calling tools to access passages, annotations,
    cross-references, and library content.
    """

    def __init__(self, model: str = "glm"):
        """Initialize the agent.

        Args:
            model: Model name from lm.py registry (default: 'glm')
        """
        from api.lm import configure_chat_lm

        self.model = model
        self.lm = configure_chat_lm(model)
        self.react = dspy.ReAct(
            signature=OSBSignature,
            tools=TOOLS,
            max_iters=MAX_TOOL_ITERATIONS,
        )
        logger.info(f"OSBAgent initialized with model={model}, {len(TOOLS)} tools")
        chat_logger.debug(f"OSBAgent initialized: model={model}, tools={[t.name for t in TOOLS]}")

    async def forward(
        self,
        messages: list[ChatMessage],
        reading_context: ReadingContext | None = None,
    ) -> ChatResponse:
        """Process a chat request.

        Args:
            messages: Full conversation history including current question
            reading_context: Current reading position (OSB passage or library node)

        Returns:
            ChatResponse with assistant message and tool call log
        """
        request_id = datetime.now().strftime("%H%M%S%f")[:10]

        if not messages:
            return ChatResponse(
                message=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="I didn't receive a message. How can I help you?",
                ),
                tool_calls=[],
            )

        # Build inputs for each DSPy field
        system_str = SYSTEM_PROMPT
        context_str = await build_context(reading_context)
        history_str = await compact_history(messages[:-1])  # All but current question
        question_str = messages[-1].content

        # =================================================================
        # LOG: Full LLM Input
        # =================================================================
        _log_separator(f"NEW CHAT REQUEST [{request_id}]")

        chat_logger.debug(f"Model: {self.model}")
        chat_logger.debug(f"Reading Context: {reading_context.model_dump() if reading_context else 'None'}")
        chat_logger.debug(f"Message Count: {len(messages)}")

        _log_section("SYSTEM PROMPT", system_str)
        _log_section("READING CONTEXT (built)", context_str)
        _log_section("CONVERSATION HISTORY", history_str)
        _log_section("CURRENT QUESTION", question_str)

        chat_logger.debug("")
        chat_logger.debug("--- TOOL EXECUTION LOG ---")

        # Retry loop
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                chat_logger.debug(f"")
                chat_logger.debug(f"[Attempt {attempt + 1}/{MAX_RETRIES}]")

                # Call ReAct asynchronously
                result = await self.react.acall(
                    system=system_str,
                    reading_context=context_str,
                    conversation=history_str,
                    question=question_str,
                )

                if result and hasattr(result, 'answer') and result.answer:
                    tool_calls = self._extract_tool_calls(result)

                    # ==========================================================
                    # LOG: Final Response
                    # ==========================================================
                    _log_section("FINAL ANSWER", result.answer)

                    chat_logger.debug("")
                    chat_logger.debug(f"Tool calls made: {len(tool_calls)}")
                    for tc in tool_calls:
                        chat_logger.debug(f"  - {tc.name}({tc.arguments})")

                    _log_separator(f"END REQUEST [{request_id}]")

                    logger.info(
                        "Agent completed: %d tool calls, answer_len=%d",
                        len(tool_calls),
                        len(result.answer),
                    )

                    return ChatResponse(
                        message=ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=result.answer,
                        ),
                        tool_calls=tool_calls,
                    )

                # Empty response, retry
                chat_logger.debug("  Empty response, retrying...")
                logger.warning(f"Empty response on attempt {attempt + 1}")

            except Exception as e:
                last_error = e
                chat_logger.debug(f"  ERROR: {e}")
                logger.warning(f"ReAct attempt {attempt + 1} failed: {e}")

        # All retries exhausted
        chat_logger.debug("")
        chat_logger.debug(f"ALL RETRIES EXHAUSTED. Last error: {last_error}")
        _log_separator(f"END REQUEST [{request_id}] - FAILED")

        logger.error(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content="I apologize, but I'm having trouble responding right now. Please try again in a moment.",
            ),
            tool_calls=[],
            error=str(last_error) if last_error else "Failed to generate response",
        )

    def _extract_tool_calls(self, result) -> list[ToolCall]:
        """Extract tool calls from ReAct result for logging/transparency.

        Args:
            result: The ReAct result object

        Returns:
            List of ToolCall objects showing what tools were used
        """
        tool_calls = []

        # ReAct stores trajectory information
        # The exact attribute depends on DSPy version
        trajectory = getattr(result, 'trajectory', None) or getattr(result, 'actions', None)

        if trajectory:
            for item in trajectory:
                if hasattr(item, 'tool') and hasattr(item, 'tool_input'):
                    tool_calls.append(ToolCall(
                        name=item.tool,
                        arguments=item.tool_input if isinstance(item.tool_input, dict) else {"input": item.tool_input},
                        result=getattr(item, 'observation', None),
                    ))
                elif isinstance(item, dict):
                    if 'tool' in item:
                        tool_calls.append(ToolCall(
                            name=item.get('tool', 'unknown'),
                            arguments=item.get('tool_input', {}),
                            result=item.get('observation'),
                        ))

        return tool_calls


# =============================================================================
# Module Interface
# =============================================================================

# Singleton agent instance
_agent: OSBAgent | None = None


def get_agent(model: str = "glm") -> OSBAgent:
    """Get or create the singleton agent instance.

    Args:
        model: Model name (only used on first call)

    Returns:
        The OSBAgent instance
    """
    global _agent
    if _agent is None:
        _agent = OSBAgent(model=model)
    return _agent


async def process_chat(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
) -> ChatResponse:
    """Process a chat request with the OSB agent.

    This is the main entry point called by the router.

    Args:
        messages: Conversation history from frontend
        context: Current reading context

    Returns:
        ChatResponse with assistant message and tool calls
    """
    agent = get_agent()
    return await agent.forward(messages, context)
