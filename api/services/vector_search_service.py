"""Vector search service for semantic search across OSB and Library content.

Uses Pinecone for vector storage and Voyage AI for embeddings.
Provides search functions optimized for the chat agent's tool usage.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from api.config import settings
from api.db import MongoDB

logger = logging.getLogger(__name__)

# Lazy-loaded clients
_voyage_client = None
_pinecone_index = None


def _get_voyage_client():
    """Lazy initialization of Voyage AI client."""
    global _voyage_client
    if _voyage_client is None:
        if not settings.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY not configured")
        import voyageai
        _voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
    return _voyage_client


def _get_pinecone_index():
    """Lazy initialization of Pinecone index."""
    global _pinecone_index
    if _pinecone_index is None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY not configured")
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    return _pinecone_index


def _embed_query(query: str) -> list[float]:
    """Generate embedding for a search query using Voyage AI."""
    client = _get_voyage_client()
    result = client.embed(
        texts=[query],
        model=settings.embedding_model_name,
        input_type="query",
        output_dimension=2048,
    )
    return result.embeddings[0]


@dataclass
class OSBSearchResult:
    """A single OSB search result with resolved metadata."""
    source_type: str  # osb_study, osb_article, osb_chapter
    score: float
    text: str
    # For study notes and articles
    annotation_id: Optional[str] = None
    # For all types
    book_id: Optional[str] = None
    book_name: Optional[str] = None
    chapter: Optional[int] = None
    verse_start: Optional[int] = None
    verse_end: Optional[int] = None
    passage_ids: Optional[list[str]] = None


@dataclass
class LibrarySearchResult:
    """A single library search result."""
    score: float
    text: str
    work_id: str
    node_id: str
    node_title: Optional[str] = None
    author_id: Optional[str] = None
    work_title: Optional[str] = None
    author_name: Optional[str] = None
    chunk_sequence: Optional[int] = None
    scripture_refs: Optional[list[str]] = None


async def search_osb(
    query: str,
    top_k: int = 3,
    source_type_filter: Optional[str] = None,
) -> list[OSBSearchResult]:
    """Search OSB content (study notes, articles, chapter text).

    Args:
        query: Natural language search query
        top_k: Number of results to return
        source_type_filter: Optional filter for source_type (osb_study, osb_article, osb_chapter)

    Returns:
        List of OSBSearchResult with resolved metadata
    """
    try:
        query_embedding = _embed_query(query)
        index = _get_pinecone_index()

        # Build filter if specified
        filter_dict = None
        if source_type_filter:
            filter_dict = {"source_type": {"$eq": source_type_filter}}

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict,
            namespace="osb",
            include_metadata=True,
        )

        search_results = []
        min_score = settings.vector_search_min_score

        for match in results.matches:
            # Filter by score threshold
            if match.score < min_score:
                continue

            meta = match.metadata or {}

            result = OSBSearchResult(
                source_type=meta.get("source_type", "unknown"),
                score=match.score,
                text=meta.get("text", ""),
                annotation_id=meta.get("annotation_id"),
                book_id=meta.get("book_id"),
                book_name=meta.get("book_name"),
                chapter=meta.get("chapter"),
                verse_start=meta.get("verse_start"),
                verse_end=meta.get("verse_end"),
                passage_ids=meta.get("passage_ids"),
            )
            search_results.append(result)

        return search_results

    except Exception as e:
        logger.error(f"OSB search failed: {e}")
        # Also log to chat logger so it appears in chat.log
        import logging
        chat_logger = logging.getLogger("api.chat.llm")
        chat_logger.debug(f"    !!! SEARCH ERROR: {e}")
        return []


async def search_library(
    query: str,
    top_k: int = 3,
    author_filter: Optional[str] = None,
    work_filter: Optional[str] = None,
) -> list[LibrarySearchResult]:
    """Search library content (patristic works, spiritual texts).

    Args:
        query: Natural language search query
        top_k: Number of results to return
        author_filter: Optional filter by author_id
        work_filter: Optional filter by work_id

    Returns:
        List of LibrarySearchResult with chunk text and node IDs
    """
    try:
        query_embedding = _embed_query(query)
        index = _get_pinecone_index()

        # Build filter
        filter_dict = {}
        if author_filter:
            filter_dict["author_id"] = {"$eq": author_filter}
        if work_filter:
            filter_dict["work_id"] = {"$eq": work_filter}

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict if filter_dict else None,
            namespace="library",
            include_metadata=True,
        )

        # Filter by score threshold first
        min_score = settings.vector_search_min_score
        valid_matches = [m for m in results.matches if m.score >= min_score]

        if not valid_matches:
            return []

        # Collect all vector IDs to look up logical node IDs from MongoDB
        vector_ids = [m.id for m in valid_matches]

        # Query MongoDB nodes collection to resolve vector_id -> logical id
        # Each node has pinecone_vector_id array containing its chunk vector IDs
        # Exclude HIDDEN nodes from search results
        db = MongoDB.db_dox
        node_docs = await db.library_nodes.find(
            {"pinecone_vector_id": {"$in": vector_ids}, "status": {"$ne": "HIDE"}},
            {"_id": 1, "pinecone_vector_id": 1}
        ).to_list(length=None)

        # Build mapping: vector_id -> logical node id
        vector_to_node_id: dict[str, str] = {}
        for doc in node_docs:
            logical_id = doc.get("_id", "")
            for vid in doc.get("pinecone_vector_id", []):
                vector_to_node_id[vid] = logical_id

        # Collect unique work_ids and author_ids to resolve titles/names
        work_ids = list({m.metadata.get("work_id") for m in valid_matches if m.metadata and m.metadata.get("work_id")})

        # Look up works to get titles and author_ids
        work_docs = await db.library_works.find(
            {"_id": {"$in": work_ids}},
            {"_id": 1, "title": 1, "author_id": 1}
        ).to_list(length=None)

        work_titles: dict[str, str] = {}
        work_author_ids: dict[str, str] = {}
        for doc in work_docs:
            work_titles[doc["_id"]] = doc.get("title", "")
            if doc.get("author_id"):
                work_author_ids[doc["_id"]] = doc["author_id"]

        # Collect all author_ids and resolve to display names
        author_ids = list(set(work_author_ids.values()))
        author_docs = await db.library_authors.find(
            {"_id": {"$in": author_ids}},
            {"_id": 1, "display_name": 1}
        ).to_list(length=None)
        author_names: dict[str, str] = {doc["_id"]: doc.get("display_name", doc["_id"]) for doc in author_docs}

        # Build results with resolved node IDs, work titles, and author names
        search_results = []
        for match in valid_matches:
            meta = match.metadata or {}

            # Look up logical node_id, fall back to metadata node_id if not found
            resolved_node_id = vector_to_node_id.get(match.id, meta.get("node_id", ""))
            work_id = meta.get("work_id", "")
            author_id = meta.get("author_id") or work_author_ids.get(work_id)

            result = LibrarySearchResult(
                score=match.score,
                text=meta.get("text", ""),
                work_id=work_id,
                node_id=resolved_node_id,
                node_title=meta.get("node_title"),
                author_id=author_id,
                work_title=work_titles.get(work_id),
                author_name=author_names.get(author_id) if author_id else None,
                chunk_sequence=meta.get("chunk_sequence"),
                scripture_refs=meta.get("scripture_refs"),
            )
            search_results.append(result)

        return search_results

    except Exception as e:
        logger.error(f"Library search failed: {e}")
        # Also log to chat logger so it appears in chat.log
        import logging
        chat_logger = logging.getLogger("api.chat.llm")
        chat_logger.debug(f"    !!! SEARCH ERROR: {e}")
        return []
