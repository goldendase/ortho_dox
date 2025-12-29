"""Relevance judge for semantic search results.

Uses Gemini Flash to filter out vector search results that look semantically
similar but aren't actually relevant to the user's question in context.

Judges all results in a single aggregate call for cost efficiency.
"""

import asyncio
import logging
from typing import TypeVar

import dspy

from api.lm import get_lm

logger = logging.getLogger(__name__)

# Dedicated judge LM - fast model for evaluation
_judge_lm: dspy.LM | None = None


def _get_judge_lm() -> dspy.LM:
    """Get or initialize the Gemini Flash judge LM."""
    global _judge_lm
    if _judge_lm is None:
        _judge_lm = get_lm("gemini-flash", temperature=0.0)  # Deterministic for consistency
    return _judge_lm


class RelevanceJudgeSignature(dspy.Signature):
    """Judge which search results are truly relevant to the user's question.

    You are a relevance judge for a theological study application. Given the conversation
    context and a list of search results, determine which results actually help answer
    the user's question.

    Be strict: A result is only relevant if it directly addresses the topic the user asked about.
    Results that are merely related by keywords or tangentially connected should be filtered out.

    Return the indices (0-based) of results that ARE relevant as a comma-separated list.
    If no results are relevant, return "none".
    """

    chat_context: str = dspy.InputField(
        desc="Recent conversation history showing what the user is asking about"
    )
    query: str = dspy.InputField(
        desc="The search query that was used to find these results"
    )
    results: str = dspy.InputField(
        desc="Numbered list of search results to evaluate"
    )
    relevant_indices: str = dspy.OutputField(
        desc="Comma-separated indices of relevant results (e.g., '0,2,4'), or 'none' if none are relevant"
    )


def _format_results_for_judge(results: list, text_extractor: callable) -> str:
    """Format results as a numbered list for the judge."""
    lines = []
    for i, result in enumerate(results):
        text = text_extractor(result)
        # Truncate each result for the judge
        if len(text) > 800:
            text = text[:800] + "..."
        lines.append(f"[{i}] {text}")
    return "\n\n".join(lines)


def _parse_relevant_indices(response: str, max_index: int) -> list[int]:
    """Parse the judge's response into a list of valid indices."""
    response = response.strip().lower()

    if response == "none" or not response:
        return []

    indices = []
    for part in response.replace(" ", "").split(","):
        try:
            idx = int(part)
            if 0 <= idx <= max_index:
                indices.append(idx)
        except ValueError:
            continue

    return indices


T = TypeVar('T')


async def filter_by_relevance(
    results: list[T],
    query: str,
    chat_context: str,
    text_extractor: callable,
) -> list[T]:
    """Filter search results by relevance using Gemini Flash judge.

    Makes a single aggregate call to judge all results together for cost efficiency.

    Args:
        results: List of search results to filter
        query: The original search query
        chat_context: Full conversation history for context
        text_extractor: Function to extract text from each result for judging

    Returns:
        Filtered list containing only relevant results
    """
    if not results:
        return results

    if not chat_context.strip():
        # No context to judge against, return all results
        logger.debug("No chat context provided, skipping relevance judge")
        return results

    lm = _get_judge_lm()
    judge = dspy.Predict(RelevanceJudgeSignature)

    # Format all results for the judge
    formatted_results = _format_results_for_judge(results, text_extractor)

    try:
        # Single aggregate judge call
        with dspy.context(lm=lm):
            response = await asyncio.to_thread(
                judge,
                chat_context=chat_context,
                query=query,
                results=formatted_results,
            )

        # Parse which indices are relevant
        relevant_indices = _parse_relevant_indices(
            response.relevant_indices,
            max_index=len(results) - 1,
        )

        # Filter results
        filtered = [results[i] for i in relevant_indices]

        logger.info(
            f"Relevance judge: {len(filtered)}/{len(results)} results passed "
            f"(indices: {relevant_indices}, query: {query[:50]}...)"
        )

        return filtered

    except Exception as e:
        logger.warning(f"Relevance judge failed: {e}, returning all results")
        # Fail-open: return all results if judge fails
        return results
