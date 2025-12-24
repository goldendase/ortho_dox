"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.db import MongoDB
from api.routers import annotations, books, chat, context, passages, patristic

# Logging setup
LOG_DIR = Path(__file__).parent.parent / "log"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

# Configure root logger for file output (warnings only)
logging.root.addHandler(file_handler)

# Get our app logger
logger = logging.getLogger("api")
logger.setLevel(logging.WARNING)

API_DESCRIPTION = """
REST API for the Orthodox Study Bible, serving verse text, patristic commentary,
cross-references, and liturgical notes from MongoDB.

## Consumers

- **Reader Application**: Fast chapter display with inline annotations
- **MCP Server**: Rich theological context for LLM consumption

## Key Features

- **Expand modes**: Control response detail level (`none`, `annotations`, `full`)
- **Bidirectional cross-refs**: Find passages that reference a verse, not just what it references
- **Patristic citations**: 53 Church Fathers with citation counts
- **LXX numbering**: Psalms use Septuagint numbering (Psalm 22 = "The Lord is my shepherd")

## Data Notes

- Passage IDs are opaque keys (e.g., `Gen_vchap1-1`) - don't parse them
- Text preserves semantic `<i>` and `<b>` markup intentionally
- 78 canonical books (full Orthodox Old Testament + New Testament)
"""

TAGS_METADATA = [
    {
        "name": "books",
        "description": "Navigate the 78 canonical books and their chapters.",
    },
    {
        "name": "passages",
        "description": "Retrieve verse text with configurable expansion of annotations and cross-references.",
    },
    {
        "name": "annotations",
        "description": "Query study notes, liturgical notes, textual variants, and topical articles.",
    },
    {
        "name": "patristic",
        "description": "Explore the 53 Church Fathers cited in the study notes.",
    },
    {
        "name": "context",
        "description": "MCP-focused endpoints providing rich context bundles for LLM consumption.",
    },
    {
        "name": "chat",
        "description": "Chat with the OSB study assistant (Michael) using GLM-4.7 with tool access to the database.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    await MongoDB.connect()
    yield
    await MongoDB.close()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

# CORS middleware
origins = (
    ["*"] if settings.cors_origins == "*"
    else [o.strip() for o in settings.cors_origins.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return clean validation error messages."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(l) for l in error["loc"])
        errors.append({"field": loc, "message": error["msg"]})
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Routers
app.include_router(books.router)
app.include_router(passages.router)
app.include_router(annotations.router)
app.include_router(patristic.router)
app.include_router(context.router)
app.include_router(chat.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
