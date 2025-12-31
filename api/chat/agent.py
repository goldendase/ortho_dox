"""OSB Chat Agent using DSPy ReAct.

This module implements the chat agent using DSPy's ReAct pattern with native
tool calling. The agent has access to tools for querying Scripture, study notes,
patristic commentary, and the theological library.
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable

import dspy

from api.chat.context_builder import build_context
from api.chat.history import compact_history
from api.chat.tools import TOOLS as RAW_TOOLS, set_chat_context
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
# Tool Wrapper for Logging with Timing
# =============================================================================

# Per-request tool timing storage (reset each request)
_tool_timings: list[tuple[str, float]] = []


def _reset_tool_timings():
    """Reset tool timings for a new request."""
    global _tool_timings
    _tool_timings = []


def _get_tool_timings() -> list[tuple[str, float]]:
    """Get tool timings for current request."""
    return _tool_timings


def _wrap_tool_with_logging(tool: dspy.Tool) -> dspy.Tool:
    """Wrap a tool's function to log inputs, outputs, and timing."""
    original_func = tool.func

    @wraps(original_func)
    async def logged_func(*args, **kwargs):
        global _tool_timings

        # Log tool invocation
        chat_logger.debug("")
        chat_logger.debug(f">>> TOOL CALL: {tool.name}")
        chat_logger.debug(f"    Arguments: {json.dumps(kwargs, default=str)}")

        start_time = time.perf_counter()
        try:
            result = await original_func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time

            # Record timing
            _tool_timings.append((tool.name, elapsed))

            # Log result with timing
            result_str = str(result)
            chat_logger.debug(f"    Time: {elapsed:.3f}s")
            if len(result_str) > 2000:
                chat_logger.debug(f"    Result: {result_str[:2000]}")
                chat_logger.debug(f"    ... [{len(result_str) - 2000} more chars]")
            else:
                chat_logger.debug(f"    Result: {result_str}")

            return result

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            _tool_timings.append((tool.name, elapsed))
            chat_logger.debug(f"    Time: {elapsed:.3f}s")
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
MAX_TOOL_ITERATIONS = 10


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
        request_start = time.perf_counter()
        _reset_tool_timings()

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

        # Check for debug mode flag
        debug_mode = "@debug@" in question_str
        if debug_mode:
            # Strip the debug flag from the question sent to the LLM
            question_str = question_str.replace("@debug@", "").strip()

        # =================================================================
        # LOG: Full LLM Input
        # =================================================================
        _log_separator(f"NEW CHAT REQUEST [{request_id}]")

        chat_logger.debug(f"Model: {self.model}")
        chat_logger.debug(f"Reading Context: {reading_context.model_dump() if reading_context else 'None'}")
        chat_logger.debug(f"Message Count: {len(messages)}")

        _log_section("READING CONTEXT (built)", context_str)
        _log_section("CONVERSATION HISTORY", history_str)
        _log_section("CURRENT QUESTION", question_str)

        chat_logger.debug("")
        chat_logger.debug("--- TOOL EXECUTION LOG ---")

        # Set chat context for relevance judge in search tools
        # Include history + current question so judge has full context
        judge_context = f"{history_str}\n\nUser: {question_str}" if history_str else f"User: {question_str}"
        set_chat_context(judge_context)

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

                # ALWAYS extract and log trajectory (even if answer is empty/missing)
                tool_calls, reasoning_steps = [], []
                if result:
                    tool_calls, reasoning_steps = self._extract_trajectory(result)

                # ==========================================================
                # LOG: LLM Reasoning (ALWAYS logged when available)
                # ==========================================================
                if reasoning_steps:
                    chat_logger.debug("")
                    chat_logger.debug("╔══════════════════════════════════════════════════════════════════════════════╗")
                    chat_logger.debug("║                           LLM REASONING / THINKING                           ║")
                    chat_logger.debug("╚══════════════════════════════════════════════════════════════════════════════╝")
                    for i, thought in enumerate(reasoning_steps, 1):
                        chat_logger.debug(f"")
                        chat_logger.debug(f"[Step {i}]")
                        chat_logger.debug(thought)
                    chat_logger.debug("")
                    chat_logger.debug("════════════════════════════════════════════════════════════════════════════════")

                if result and hasattr(result, 'answer') and result.answer:
                    # ==========================================================
                    # LOG: Final Response
                    # ==========================================================
                    _log_section("FINAL ANSWER", result.answer)

                    # Timing summary
                    total_time = time.perf_counter() - request_start
                    tool_timings = _get_tool_timings()
                    total_tool_time = sum(t for _, t in tool_timings)

                    chat_logger.debug("")
                    chat_logger.debug("--- TIMING SUMMARY ---")
                    chat_logger.debug(f"Total request time: {total_time:.3f}s")
                    chat_logger.debug(f"Total tool time:    {total_tool_time:.3f}s")
                    chat_logger.debug(f"LLM/other time:     {total_time - total_tool_time:.3f}s")
                    chat_logger.debug(f"Tool calls made: {len(tool_calls)}")
                    for name, elapsed in tool_timings:
                        chat_logger.debug(f"  - {name}: {elapsed:.3f}s")

                    _log_separator(f"END REQUEST [{request_id}]")

                    logger.info(
                        "Agent completed: %d tool calls, answer_len=%d",
                        len(tool_calls),
                        len(result.answer),
                    )

                    # Build final answer, optionally with debug info
                    final_answer = result.answer
                    if debug_mode:
                        debug_lines = ["[DEBUG]"]
                        # Add reasoning
                        if reasoning_steps:
                            debug_lines.append("**Reasoning:**")
                            for i, thought in enumerate(reasoning_steps, 1):
                                debug_lines.append(f"{i}. {thought}")
                            debug_lines.append("")
                        # Add tool calls (name and args only, no results)
                        if tool_calls:
                            debug_lines.append("**Tool Calls:**")
                            for tc in tool_calls:
                                args_str = json.dumps(tc.arguments, default=str)
                                debug_lines.append(f"- `{tc.name}({args_str})`")
                        debug_lines.append("[/DEBUG]")
                        debug_lines.append("")
                        final_answer = "\n".join(debug_lines) + final_answer

                    return ChatResponse(
                        message=ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=final_answer,
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
        total_time = time.perf_counter() - request_start
        tool_timings = _get_tool_timings()
        total_tool_time = sum(t for _, t in tool_timings)

        chat_logger.debug("")
        chat_logger.debug(f"ALL RETRIES EXHAUSTED. Last error: {last_error}")
        chat_logger.debug("")
        chat_logger.debug("--- TIMING SUMMARY (FAILED) ---")
        chat_logger.debug(f"Total request time: {total_time:.3f}s")
        chat_logger.debug(f"Total tool time:    {total_tool_time:.3f}s")
        for name, elapsed in tool_timings:
            chat_logger.debug(f"  - {name}: {elapsed:.3f}s")
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

    def _extract_trajectory(self, result) -> tuple[list[ToolCall], list[str]]:
        """Extract tool calls and reasoning from ReAct result.

        DSPy ReAct stores trajectory as a dict with indexed keys:
        - thought_0, thought_1, ... (reasoning at each step)
        - tool_name_0, tool_name_1, ... (tool selected)
        - tool_args_0, tool_args_1, ... (arguments as dict)
        - observation_0, observation_1, ... (tool results)

        Args:
            result: The ReAct result (dspy.Prediction with trajectory attribute)

        Returns:
            Tuple of (tool_calls, reasoning_steps)
        """
        tool_calls = []
        reasoning_steps = []

        trajectory = getattr(result, 'trajectory', None)

        if trajectory and isinstance(trajectory, dict):
            # Find how many iterations occurred by looking for thought_N keys
            idx = 0
            while f"thought_{idx}" in trajectory or f"tool_name_{idx}" in trajectory:
                # Extract reasoning/thought for this step
                thought = trajectory.get(f"thought_{idx}")
                if thought:
                    reasoning_steps.append(str(thought))

                # Extract tool call for this step
                tool_name = trajectory.get(f"tool_name_{idx}")
                tool_args = trajectory.get(f"tool_args_{idx}", {})
                observation = trajectory.get(f"observation_{idx}")

                if tool_name and tool_name != "finish":
                    tool_calls.append(ToolCall(
                        name=tool_name,
                        arguments=tool_args if isinstance(tool_args, dict) else {"input": tool_args},
                        result=observation,
                    ))

                idx += 1

        return tool_calls, reasoning_steps

    def _extract_tool_calls(self, result) -> list[ToolCall]:
        """Extract tool calls from ReAct result for logging/transparency.

        Args:
            result: The ReAct result object

        Returns:
            List of ToolCall objects showing what tools were used
        """
        tool_calls, _ = self._extract_trajectory(result)
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
