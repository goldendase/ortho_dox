"""Chat endpoint for OSB agent conversations."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.models.chat import ChatRequest, ChatResponse
from api.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message with the OSB study assistant.

    The frontend manages conversation history and sends the full message list
    with each request. The agent has access to tools for querying:

    - **Passages**: Retrieve verses with study notes and patristic commentary
    - **Chapters**: Get all verses in a chapter
    - **Context**: Cross-references, related passages, patristic sources
    - **Annotations**: Search study notes by type or Church Father
    - **Library**: Browse and read theological works (patristic texts, biographies)

    **Request body:**
    - `messages`: List of conversation messages (role: user/assistant/system)
    - `context`: Optional reading context with:
        - OSB context: `passage_id` or `book_id` + `chapter`
        - Library context: `work_id` + optional `node_id`

    **Response:**
    - `message`: The assistant's response
    - `tool_calls`: Tools called during processing (for debugging)
    - `error`: Error message if something went wrong

    The agent uses DSPy ReAct with native tool calling, with up to 3 retries.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    return await chat_service.process_chat(
        messages=request.messages,
        context=request.context,
        model=request.model,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Process a chat message with streaming response (SSE).

    Same as `/chat` but returns Server-Sent Events for real-time updates.
    The frontend receives events as they happen:

    **Event types:**
    - `chunk`: Raw DSPy output including markers like [[ ## next_thought ## ]]
    - `done`: Final complete response with answer and tool_calls
    - `error`: Error occurred during processing

    **SSE format:**
    ```
    data: {"type": "chunk", "data": "The passage..."}

    data: {"type": "done", "data": {"answer": "...", "tool_calls": [...]}}
    ```

    **Cancellation:**
    The `X-Stream-ID` response header contains the stream ID.
    POST to `/chat/stream/{stream_id}/cancel` to stop the stream.

    **Usage (JavaScript):**
    ```javascript
    const response = await fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages, context })
    });
    const streamId = response.headers.get('X-Stream-ID');
    const reader = response.body.getReader();
    // Process SSE chunks...
    ```
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    stream_id = chat_service.generate_stream_id()

    async def event_generator():
        """Generate SSE events from the streaming agent."""
        async for event in chat_service.process_chat_stream(
            messages=request.messages,
            context=request.context,
            stream_id=stream_id,
            model=request.model,
        ):
            # Format as SSE: data: {json}\n\n
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Stream-ID": stream_id,
        },
    )


class CancelResponse(BaseModel):
    """Response for stream cancellation."""
    cancelled: bool
    stream_id: str


@router.post("/stream/{stream_id}/cancel", response_model=CancelResponse)
async def cancel_stream(stream_id: str) -> CancelResponse:
    """
    Cancel an active chat stream.

    Args:
        stream_id: The stream ID from the X-Stream-ID header

    Returns:
        Whether the stream was found and cancelled
    """
    cancelled = chat_service.cancel_stream(stream_id)
    return CancelResponse(cancelled=cancelled, stream_id=stream_id)
