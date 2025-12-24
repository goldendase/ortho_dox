"""Chat service with OSB agent tooling using DSPy."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import dspy
import httpx

from api.models.chat import ChatMessage, ChatResponse, MessageRole, ReadingContext, ToolCall
from api.models.common import AnnotationType, ExpandMode, Testament
from api.services import annotation_service, book_service, context_service, passage_service

logger = logging.getLogger(__name__)

# Chat-specific logger for detailed LLM interaction logging
chat_logger = logging.getLogger("api.chat")

# Set up file handler for chat logs
CHAT_LOG_DIR = Path(__file__).parent.parent.parent / "log"
CHAT_LOG_DIR.mkdir(exist_ok=True)
CHAT_LOG_FILE = CHAT_LOG_DIR / "chat.log"

_chat_handler = logging.FileHandler(CHAT_LOG_FILE)
_chat_handler.setLevel(logging.DEBUG)
_chat_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
chat_logger.addHandler(_chat_handler)
chat_logger.setLevel(logging.DEBUG)

# Load system prompt
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "osb_agent_system_prompt.md").read_text()

# Model configuration
MODEL = "z-ai/glm-4.7"
FALLBACK_PROVIDERS = ["z-ai", "parasail"]
MAX_RETRIES = 3
MAX_TOOL_ROUNDS = 10


# =============================================================================
# Tool Functions (async, will be wrapped with dspy.Tool)
# =============================================================================


async def get_passage(passage_id: str) -> str:
    """
    Retrieve a single Bible passage by its ID with full study notes, patristic
    citations, and cross-references. Use this when the user asks about a specific
    verse or when you need detailed commentary on a passage.

    Passage IDs follow the format: {BookAbbr}_vchap{Chapter}-{Verse}
    Examples: 'Gen_vchap1-1' (Genesis 1:1), 'Matt_vchap5-3' (Matthew 5:3),
    'Ps_vchap22-1' (Psalm 22:1 - LXX numbering, this is "The Lord is my shepherd")

    Args:
        passage_id: The passage ID, e.g., 'Gen_vchap1-1', 'John_vchap3-16'

    Returns:
        JSON string with passage text, study notes, patristic citations, cross-refs
    """
    passage = await passage_service.get_passage(
        passage_id, expand=ExpandMode.FULL, include_html=False
    )
    if not passage:
        return json.dumps({"error": f"Passage not found: {passage_id}"})
    return json.dumps(passage.model_dump(), default=str)


async def get_chapter_passages(
    book_id: str,
    chapter: int,
    verse_start: int | None = None,
    verse_end: int | None = None,
) -> str:
    """
    Retrieve all verses in a chapter with their study notes and annotations.
    Use this when discussing an entire chapter or when the user wants to read
    through a section of Scripture.

    Args:
        book_id: Lowercase book ID, e.g., 'genesis', 'matthew', 'psalms', '1corinthians'
        chapter: Chapter number (1-indexed)
        verse_start: Optional first verse to return (for partial chapter)
        verse_end: Optional last verse to return (for partial chapter)

    Returns:
        JSON string with all passages in the chapter
    """
    passages, navigation = await passage_service.get_chapter_passages(
        book_id, chapter, ExpandMode.ANNOTATIONS, verse_start, verse_end
    )
    if not passages:
        return json.dumps({"error": f"No passages found for {book_id} chapter {chapter}"})
    return json.dumps({
        "book_id": book_id,
        "chapter": chapter,
        "passages": [p.model_dump() for p in passages],
        "total": len(passages),
        "navigation": navigation.model_dump(),
    }, default=str)


async def get_passage_context(passage_id: str) -> str:
    """
    Get rich theological context for a passage, including bidirectional
    cross-references (passages it references AND passages that reference it),
    all patristic sources cited in annotations, and related topical articles.

    Use this when exploring connections between passages or when the user
    asks 'what other passages relate to this?' or wants to understand a
    verse in its broader scriptural context.

    Args:
        passage_id: The passage ID to get context for

    Returns:
        JSON with passage, cross_references (outgoing/incoming), patristic_sources, related_articles
    """
    context = await context_service.get_passage_context(passage_id)
    if not context:
        return json.dumps({"error": f"Passage not found: {passage_id}"})
    return json.dumps(context.model_dump(), default=str)


async def search_annotations(
    annotation_type: str | None = None,
    patristic_source: str | None = None,
    book_id: str | None = None,
    limit: int = 20,
) -> str:
    """
    Search study notes and annotations by type and/or patristic source.

    Annotation types:
    - 'study': Patristic commentary and theological notes (6,290 total)
    - 'liturgical': Liturgical usage references (365 total)
    - 'variant': NT manuscript variants, NU-Text vs M-Text (932 total)
    - 'citation': Cross-reference notes like "See note at X" (229 total)
    - 'article': Topical study essays (47 total)

    Use this to find what the Church Fathers say on topics or to explore
    annotations in a specific book.

    Args:
        annotation_type: Type of annotation ('study', 'liturgical', 'variant', 'citation', 'article')
        patristic_source: Church Father ID, e.g., 'JohnChr' (Chrysostom), 'BasilG' (Basil the Great)
        book_id: Optional book ID to limit search
        limit: Maximum results (default 20, max 100)

    Returns:
        JSON with matching annotations and total count
    """
    ann_type = AnnotationType(annotation_type) if annotation_type else None
    limit = min(limit, 100)

    result = await annotation_service.get_annotations(
        type=ann_type,
        patristic_source=patristic_source,
        book_id=book_id,
        limit=limit,
        offset=0,
    )
    return json.dumps(result.model_dump(), default=str)


async def get_patristic_sources() -> str:
    """
    List all 53 Church Fathers cited in the OSB study notes, sorted by
    citation count. Use this to see which Fathers are most frequently cited
    or to look up a Father's ID for use in search_annotations.

    Top cited Fathers include: John Chrysostom (JohnChr), Basil the Great (BasilG),
    Augustine (AugHip), Cyril of Alexandria (CyrAl), Gregory the Theologian (GregNaz).

    Returns:
        JSON with list of {id, name, citation_count} sorted by citation count
    """
    result = await annotation_service.get_patristic_sources()
    return json.dumps(result.model_dump(), default=str)


async def get_book_info(book_id: str) -> str:
    """
    Get details about a biblical book: chapter count, verse count, testament,
    and chapter breakdown. Use this when the user asks about a book's structure
    or when you need to know how many chapters a book has.

    Args:
        book_id: Lowercase book ID, e.g., 'genesis', 'psalms', 'revelation', 'sirach'

    Returns:
        JSON with book details including chapters list with verse counts
    """
    book = await book_service.get_book(book_id)
    if not book:
        return json.dumps({"error": f"Book not found: {book_id}"})
    return json.dumps(book.model_dump(), default=str)


async def list_books(testament: str | None = None) -> str:
    """
    List all 78 canonical books of the Orthodox Bible. Can filter by testament.

    The Orthodox canon includes books Western Christians call 'deuterocanonical'
    or 'apocrypha': Tobit, Judith, Wisdom of Solomon, Sirach (Ecclesiasticus),
    Baruch, Letter of Jeremiah, 1-4 Maccabees, additions to Esther and Daniel.
    These are simply Scripture in the Orthodox Church.

    Args:
        testament: Optional filter - 'old' (OT, 49 books) or 'new' (NT, 29 books)

    Returns:
        JSON with list of books (id, name, abbreviation, chapter_count, etc.)
    """
    test = Testament(testament) if testament else None
    result = await book_service.get_books(test)
    return json.dumps(result.model_dump(), default=str)


# =============================================================================
# DSPy Tool Definitions
# =============================================================================

# Wrap async functions with dspy.Tool
# Note: dspy.Tool expects sync functions, but we'll handle async execution ourselves
TOOLS = [
    dspy.Tool(
        func=get_passage,
        name="get_passage",
        desc="Retrieve a Bible passage by ID with study notes and patristic commentary",
        args={"passage_id": "Passage ID like 'Gen_vchap1-1' or 'John_vchap3-16'"},
    ),
    dspy.Tool(
        func=get_chapter_passages,
        name="get_chapter_passages",
        desc="Get all verses in a chapter with annotations",
        args={
            "book_id": "Lowercase book ID like 'genesis' or 'matthew'",
            "chapter": "Chapter number (integer)",
            "verse_start": "Optional: first verse number",
            "verse_end": "Optional: last verse number",
        },
    ),
    dspy.Tool(
        func=get_passage_context,
        name="get_passage_context",
        desc="Get rich context: cross-references, patristic sources, related articles",
        args={"passage_id": "Passage ID to get context for"},
    ),
    dspy.Tool(
        func=search_annotations,
        name="search_annotations",
        desc="Search study notes by type (study/liturgical/variant/citation/article) or Church Father",
        args={
            "annotation_type": "Optional: 'study', 'liturgical', 'variant', 'citation', or 'article'",
            "patristic_source": "Optional: Father ID like 'JohnChr' or 'BasilG'",
            "book_id": "Optional: limit to a book",
            "limit": "Optional: max results (default 20)",
        },
    ),
    dspy.Tool(
        func=get_patristic_sources,
        name="get_patristic_sources",
        desc="List all 53 Church Fathers cited in the OSB with citation counts",
        args={},
    ),
    dspy.Tool(
        func=get_book_info,
        name="get_book_info",
        desc="Get book details: chapters, verses, testament",
        args={"book_id": "Lowercase book ID like 'genesis' or 'psalms'"},
    ),
    dspy.Tool(
        func=list_books,
        name="list_books",
        desc="List all 78 Orthodox canon books, optionally filtered by testament",
        args={"testament": "Optional: 'old' or 'new'"},
    ),
]

# Build lookup for execution
TOOL_MAP = {tool.name: tool for tool in TOOLS}


def _tools_to_openai_format() -> list[dict]:
    """Convert dspy.Tool definitions to OpenAI function calling format."""
    openai_tools = []
    for tool in TOOLS:
        # Build parameters schema from args
        properties = {}
        required = []
        for arg_name, arg_desc in tool.args.items():
            # Infer type from description or default to string
            if "integer" in arg_desc.lower() or arg_name in ("chapter", "limit", "verse_start", "verse_end"):
                properties[arg_name] = {"type": "integer", "description": arg_desc}
            else:
                properties[arg_name] = {"type": "string", "description": arg_desc}

            # Mark as required if not "Optional"
            if "optional" not in arg_desc.lower():
                required.append(arg_name)

        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.func.__doc__ or tool.desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return openai_tools


OPENAI_TOOLS = _tools_to_openai_format()


# =============================================================================
# OSB Agent Module
# =============================================================================


class OSBAgent(dspy.Module):
    """
    Orthodox Study Bible chat agent using native function calling.

    This module handles conversations about Scripture, using tools to access
    the OSB database for passages, study notes, patristic commentary, and
    cross-references.
    """

    def __init__(self):
        super().__init__()
        self.tools = TOOLS
        self.tool_map = TOOL_MAP
        self.openai_tools = OPENAI_TOOLS

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        round_num: int = 1,
    ) -> dict[str, Any]:
        """Call OpenRouter API with messages and optional tools."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://osb-reader.local",
            "X-Title": "OSB Reader Chat",
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 4096,
            "provider": {
                "order": FALLBACK_PROVIDERS,
                "allow_fallbacks": False,
                "data_collection": "deny",
            },
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        # Log the LLM request
        chat_logger.debug(
            "=== LLM REQUEST (round %d) ===\nModel: %s\nMessages: %s\nTools: %s",
            round_num,
            MODEL,
            json.dumps(messages, indent=2, default=str),
            "[%d tools provided]" % len(tools) if tools else "None",
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

        # Log the LLM response
        choices = result.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            finish_reason = choices[0].get("finish_reason", "")

            chat_logger.debug(
                "=== LLM RESPONSE (round %d) ===\nFinish reason: %s\nContent: %s\nTool calls: %s",
                round_num,
                finish_reason,
                content[:500] + "..." if len(content) > 500 else content,
                json.dumps(tool_calls, indent=2) if tool_calls else "None",
            )

            # Log any "thinking" or reasoning if present (some models include this)
            if msg.get("reasoning") or msg.get("thinking"):
                chat_logger.debug(
                    "=== MODEL THINKING (round %d) ===\n%s",
                    round_num,
                    msg.get("reasoning") or msg.get("thinking"),
                )
        else:
            chat_logger.warning("=== LLM RESPONSE (round %d) === Empty choices!", round_num)

        # Log usage stats if available
        usage = result.get("usage", {})
        if usage:
            chat_logger.debug(
                "Token usage: prompt=%s, completion=%s, total=%s",
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )

        return result

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.tool_map.get(name)
        if not tool:
            chat_logger.warning("=== TOOL ERROR === Unknown tool: %s", name)
            return json.dumps({"error": f"Unknown tool: {name}"})

        chat_logger.info(
            "=== TOOL INVOCATION ===\nTool: %s\nArguments: %s",
            name,
            json.dumps(arguments, indent=2),
        )

        try:
            # Tool functions are async, call them directly
            result = await tool.func(**arguments)

            # Log result (truncated for large responses)
            result_preview = result[:1000] + "..." if len(result) > 1000 else result
            chat_logger.info(
                "=== TOOL RESULT ===\nTool: %s\nResult: %s",
                name,
                result_preview,
            )

            return result
        except Exception as e:
            logger.exception(f"Tool execution error: {name}")
            chat_logger.error(
                "=== TOOL ERROR ===\nTool: %s\nError: %s",
                name,
                str(e),
            )
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})

    async def _build_reading_context(self, ctx: ReadingContext | None) -> str | None:
        """Build a context message from ReadingContext."""
        if not ctx:
            return None

        # If we have a specific passage
        if ctx.passage_id:
            context = await context_service.get_passage_context(ctx.passage_id)
            if context:
                return (
                    f"[Current reading context: {context.passage.book_name} "
                    f"{context.passage.chapter}:{context.passage.verse} - "
                    f"\"{context.passage.text[:200]}{'...' if len(context.passage.text) > 200 else ''}\"]"
                )

        # If we have book + chapter (user reading a chapter, no specific verse selected)
        if ctx.book_id and ctx.chapter:
            book = await book_service.get_book(ctx.book_id)
            if book:
                # Get first few verses as context
                passages, _ = await passage_service.get_chapter_passages(
                    ctx.book_id, ctx.chapter, ExpandMode.NONE, verse_start=1, verse_end=3
                )
                if passages:
                    preview = " ".join(p.text[:100] for p in passages[:3])
                    if len(preview) > 250:
                        preview = preview[:250] + "..."
                    return (
                        f"[Current reading context: {book.name} chapter {ctx.chapter} - "
                        f"User is reading this chapter. Preview: \"{preview}\"]"
                    )
                else:
                    return f"[Current reading context: {book.name} chapter {ctx.chapter}]"

        return None

    async def forward(
        self,
        messages: list[ChatMessage],
        context: ReadingContext | None = None,
    ) -> ChatResponse:
        """
        Process a chat request through the agent loop.

        Args:
            messages: Conversation history from frontend
            context: Current reading context (passage or chapter)

        Returns:
            ChatResponse with assistant message and tool call log
        """
        # Log the incoming request
        chat_logger.info(
            "=== NEW CHAT REQUEST ===\nContext: %s\nMessage count: %d",
            context.model_dump() if context else "None",
            len(messages),
        )

        # Log user messages
        for i, msg in enumerate(messages):
            chat_logger.info(
                "=== USER INPUT [%d] ===\nRole: %s\nContent: %s",
                i + 1,
                msg.role.value,
                msg.content,
            )

        # Build messages list with system prompt
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add context about current reading location if available
        context_msg = await self._build_reading_context(context)
        if context_msg:
            chat_logger.debug("Reading context: %s", context_msg)
            api_messages.append({"role": "system", "content": context_msg})

        # Add conversation history
        for msg in messages:
            api_messages.append({"role": msg.role.value, "content": msg.content})

        tool_calls_made: list[ToolCall] = []
        rounds = 0

        while rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            retries = 0
            response_data = None

            # Retry loop for API errors or empty content
            while retries < MAX_RETRIES:
                try:
                    response_data = await self._call_llm(api_messages, self.openai_tools, rounds)

                    choices = response_data.get("choices", [])
                    if not choices:
                        retries += 1
                        logger.warning(f"Empty choices in response, retry {retries}/{MAX_RETRIES}")
                        continue

                    message = choices[0].get("message", {})
                    content = message.get("content")
                    tool_calls = message.get("tool_calls")

                    if tool_calls or content:
                        break

                    retries += 1
                    logger.warning(f"Empty content and no tool calls, retry {retries}/{MAX_RETRIES}")

                except httpx.HTTPStatusError as e:
                    retries += 1
                    logger.error(f"HTTP error {e.response.status_code}, retry {retries}/{MAX_RETRIES}")
                    if retries >= MAX_RETRIES:
                        return ChatResponse(
                            message=ChatMessage(
                                role=MessageRole.ASSISTANT,
                                content="I apologize, but I'm having trouble connecting right now. Please try again.",
                            ),
                            tool_calls=tool_calls_made,
                            error=f"HTTP error: {e.response.status_code}",
                        )
                except Exception as e:
                    retries += 1
                    logger.exception(f"LLM call error, retry {retries}/{MAX_RETRIES}")
                    if retries >= MAX_RETRIES:
                        return ChatResponse(
                            message=ChatMessage(
                                role=MessageRole.ASSISTANT,
                                content="I apologize, but I encountered an error. Please try again.",
                            ),
                            tool_calls=tool_calls_made,
                            error=str(e),
                        )

            if not response_data:
                return ChatResponse(
                    message=ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content="I was unable to generate a response. Please try rephrasing your question.",
                    ),
                    tool_calls=tool_calls_made,
                    error="Failed to get valid response after retries",
                )

            # Process the response
            message = response_data["choices"][0]["message"]
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # If no tool calls, we're done
            if not tool_calls:
                chat_logger.info(
                    "=== FINAL OUTPUT ===\nRounds: %d\nTool calls: %d\nResponse: %s",
                    rounds,
                    len(tool_calls_made),
                    content[:500] + "..." if len(content or "") > 500 else content,
                )
                return ChatResponse(
                    message=ChatMessage(role=MessageRole.ASSISTANT, content=content or ""),
                    tool_calls=tool_calls_made,
                )

            # Process tool calls
            api_messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                tool_id = tc.get("id", "")

                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                result = await self._execute_tool(tool_name, arguments)

                tool_calls_made.append(ToolCall(
                    name=tool_name,
                    arguments=arguments,
                    result=json.loads(result) if isinstance(result, str) else result,
                ))

                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result,
                })

        # Max rounds exceeded
        logger.warning("Max tool rounds exceeded")
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content="I seem to be having difficulty. Could you try asking in a different way?",
            ),
            tool_calls=tool_calls_made,
            error="Max tool call rounds exceeded",
        )


# Module instance for use by router
agent = OSBAgent()


async def process_chat(
    messages: list[ChatMessage],
    context: ReadingContext | None = None,
) -> ChatResponse:
    """
    Process a chat request with the OSB agent.

    This is the main entry point called by the router.
    """
    return await agent.forward(messages, context)
