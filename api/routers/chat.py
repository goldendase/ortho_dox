"""Chat endpoint for OSB agent conversations."""

from fastapi import APIRouter, HTTPException

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
    - **Books**: Navigate the 78-book Orthodox canon

    **Request body:**
    - `messages`: List of conversation messages (role: user/assistant/system)
    - `context`: Optional reading context with either:
        - `passage_id`: Specific verse being viewed
        - `book_id` + `chapter`: Chapter being read (no specific verse selected)

    **Response:**
    - `message`: The assistant's response
    - `tool_calls`: Tools called during processing (for debugging)
    - `error`: Error message if something went wrong

    The agent uses GLM-4.7 with up to 3 retries on errors or empty responses.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")

    return await chat_service.process_chat(
        messages=request.messages,
        context=request.context,
    )
