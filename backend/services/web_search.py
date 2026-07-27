"""
Web search service for GreenLens — provides real-time web context
to enrich greenwashing analysis with current online information.

Uses the duckduckgo-search package for reliable results without API keys.
Designed to fail gracefully — never crashes the main analysis flow.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# Timeout for the entire search operation (seconds)
_SEARCH_TIMEOUT = 5


async def search(query: str, max_results: int = 5) -> str:
    """
    Search the web for the given query and return formatted context text
    ready to inject into LLM prompts.

    Returns an empty string on any failure (network error, timeout, import error).
    Never raises exceptions to the caller.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 5)

    Returns:
        Formatted string block with search results, or "" on failure
    """
    if not query or not query.strip():
        return ""

    try:
        results = await asyncio.wait_for(
            _execute_search(query.strip(), max_results),
            timeout=_SEARCH_TIMEOUT,
        )
        if not results:
            return ""
        return _format_results(query.strip(), results)
    except asyncio.TimeoutError:
        logger.warning(f"[web_search] Timed out after {_SEARCH_TIMEOUT}s for query: {query[:80]!r}")
        return ""
    except Exception as e:
        logger.warning(f"[web_search] Failed for query {query[:80]!r}: {type(e).__name__}: {e}")
        return ""


async def search_with_sources(query: str, max_results: int = 5) -> tuple[str, list[dict]]:
    """
    Search the web and return both formatted context text AND raw source link data.

    Returns:
        Tuple of (formatted_text, source_links) where source_links is a list of
        dicts with 'title', 'url', and 'snippet' keys.
        Returns ("", []) on any failure.
    """
    if not query or not query.strip():
        return "", []

    try:
        results = await asyncio.wait_for(
            _execute_search(query.strip(), max_results),
            timeout=_SEARCH_TIMEOUT,
        )
        if not results:
            return "", []
        formatted = _format_results(query.strip(), results)
        sources = get_raw_results(results)
        return formatted, sources
    except asyncio.TimeoutError:
        logger.warning(f"[web_search] Timed out after {_SEARCH_TIMEOUT}s for query: {query[:80]!r}")
        return "", []
    except Exception as e:
        logger.warning(f"[web_search] Failed for query {query[:80]!r}: {type(e).__name__}: {e}")
        return "", []


async def _execute_search(query: str, max_results: int) -> list[dict]:
    """
    Execute the search in a thread executor (duckduckgo-search is synchronous).
    Returns a list of result dicts with 'title', 'body', and 'href' keys.
    """
    loop = asyncio.get_event_loop()

    def _sync_search():
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))

    return await loop.run_in_executor(None, _sync_search)


def _format_results(query: str, results: list[dict]) -> str:
    """
    Format search results into a text block suitable for LLM prompt injection.
    Includes source URLs so the LLM can cite direct links in its analysis.
    """
    lines = [f'REAL-TIME WEB RESEARCH (searched: "{query}"):']

    for i, result in enumerate(results, 1):
        title = result.get("title", "").strip()
        snippet = result.get("body", "").strip()
        url = result.get("href", "").strip()
        if not title and not snippet:
            continue
        # Truncate long snippets to keep prompt size reasonable
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        lines.append(f"{i}. [{title}]({url}) — {snippet}")

    # Only return if we actually got useful results
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def get_raw_results(results: list[dict]) -> list[dict]:
    """
    Extract structured source link data from raw search results.
    Returns a list of dicts with title, url, and snippet fields
    suitable for building SourceLink objects.
    """
    sources = []
    for result in results:
        title = result.get("title", "").strip()
        url = result.get("href", "").strip()
        snippet = result.get("body", "").strip()
        if not title or not url:
            continue
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        sources.append({"title": title, "url": url, "snippet": snippet})
    return sources
