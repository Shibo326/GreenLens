"""
GreenLens Web Research Service
Fetches real-time online data to enrich sustainability analysis and chat responses.

Uses DuckDuckGo search (no API key required) to find:
- Company sustainability reports and ESG ratings
- Greenwashing news and watchdog reports
- Regulatory actions and certifications verification
- Industry benchmarks and standards
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

# Max concurrent web requests
MAX_CONCURRENT_REQUESTS = 3
# Timeout per request (seconds)
REQUEST_TIMEOUT = 10.0
# Max results to return per query
MAX_RESULTS = 5


@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    source: str = ""


@dataclass
class WebResearchContext:
    """Aggregated web research context for a query."""
    query: str
    results: list[WebSearchResult] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


class WebResearchService:
    """
    Provides web research capabilities using DuckDuckGo search.
    No API key required. Can be disabled via WEB_RESEARCH_ENABLED=false.
    """

    def __init__(self):
        self._enabled = os.getenv("WEB_RESEARCH_ENABLED", "true").lower() != "false"
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            follow_redirects=True,
        )
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        status = "enabled" if self._enabled else "DISABLED"
        logger.info(f"WebResearchService initialized (DuckDuckGo search - {status})")

    async def aclose(self):
        """Close the persistent HTTP client."""
        await self._client.aclose()

    async def search(self, query: str, max_results: int = MAX_RESULTS) -> list[WebSearchResult]:
        """Search the web using DuckDuckGo HTML API."""
        if not self._enabled:
            return []
        async with self._semaphore:
            try:
                return await self._search_duckduckgo(query, max_results)
            except Exception as e:
                logger.warning(f"[WebResearch] Search failed for '{query[:50]}': {e}")
                return []

    async def _search_duckduckgo(self, query: str, max_results: int) -> list[WebSearchResult]:
        """Execute a DuckDuckGo HTML search and parse results."""
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        response = await self._client.get(url)
        response.raise_for_status()
        html = response.text
        results = self._parse_duckduckgo_html(html, max_results)
        logger.info(f"[WebResearch] '{query[:40]}' -> {len(results)} results")
        return results

    def _parse_duckduckgo_html(self, html: str, max_results: int) -> list[WebSearchResult]:
        """Parse DuckDuckGo HTML response to extract search results."""
        results = []
        result_blocks = re.findall(
            r'<div class="result results_links results_links_deep[^"]*">(.*?)</div>\s*</div>',
            html, re.DOTALL,
        )
        if not result_blocks:
            result_blocks = re.findall(
                r'<div class="result[^"]*"[^>]*>(.*?)</div>\s*(?=<div class="result|$)',
                html, re.DOTALL,
            )

        for block in result_blocks[:max_results]:
            title_match = re.search(
                r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                block, re.DOTALL,
            )
            if not title_match:
                continue
            url = title_match.group(1)
            title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()

            snippet_match = re.search(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                block, re.DOTALL,
            )
            snippet = ""
            if snippet_match:
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()

            source = ""
            url_match = re.search(
                r'<span class="result__url"[^>]*>(.*?)</span>',
                block, re.DOTALL,
            )
            if url_match:
                source = re.sub(r'<[^>]+>', '', url_match.group(1)).strip()

            if title and (url or snippet):
                if "duckduckgo.com" in url and "uddg=" in url:
                    actual_url_match = re.search(r'uddg=([^&]+)', url)
                    if actual_url_match:
                        from urllib.parse import unquote
                        url = unquote(actual_url_match.group(1))
                results.append(WebSearchResult(
                    title=title, url=url, snippet=snippet, source=source,
                ))
        return results

    async def research_company(self, company_name: str) -> WebResearchContext:
        """Research a company's sustainability practices and greenwashing history."""
        queries = [
            f"{company_name} greenwashing accusations 2024 2025",
            f"{company_name} sustainability report ESG rating",
        ]
        all_results = []
        for query in queries:
            results = await self.search(query, max_results=3)
            all_results.extend(results)
        unique_results = self._deduplicate(all_results)
        return WebResearchContext(
            query=company_name,
            results=unique_results[:MAX_RESULTS],
            summary=self._build_summary(unique_results[:MAX_RESULTS]),
        )

    async def research_claim(self, claim: str, company: str = "") -> WebResearchContext:
        """Research a specific sustainability claim to verify it."""
        search_term = f"{company} {claim}" if company else claim
        queries = [
            f'"{claim}" greenwashing fact check',
            f"{search_term} sustainability verification",
        ]
        all_results = []
        for query in queries:
            results = await self.search(query, max_results=3)
            all_results.extend(results)
        unique_results = self._deduplicate(all_results)
        return WebResearchContext(
            query=claim,
            results=unique_results[:MAX_RESULTS],
            summary=self._build_summary(unique_results[:MAX_RESULTS]),
        )

    async def research_for_analysis(
        self, doc_names: list[str], key_claims: list[str]
    ) -> WebResearchContext:
        """Research multiple claims extracted from documents."""
        companies = self._extract_company_names(doc_names)
        queries = []
        for company in companies[:2]:
            queries.append(f"{company} greenwashing sustainability credibility 2024")
        for claim in key_claims[:3]:
            queries.append(f"{claim} fact check verification")

        all_results = []
        tasks = [self.search(q, max_results=2) for q in queries]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in search_results:
            if isinstance(result, list):
                all_results.extend(result)

        unique_results = self._deduplicate(all_results)
        return WebResearchContext(
            query=f"Analysis context for: {', '.join(doc_names[:3])}",
            results=unique_results[:8],
            summary=self._build_summary(unique_results[:8]),
        )

    async def research_for_chat(self, question: str, doc_context: str = "") -> WebResearchContext:
        """Research to help answer a chat question with real-world context."""
        clean_q = re.sub(
            r'\b(what|is|the|are|does|do|can|how|why|this|that|their|they|it|was|been)\b',
            '', question.lower(),
        ).strip()
        clean_q = re.sub(r'\s+', ' ', clean_q)[:100]

        queries = [f"{clean_q} sustainability greenwashing"]
        if doc_context:
            queries.append(f"{doc_context[:60]} {clean_q[:40]}")

        all_results = []
        tasks = [self.search(q, max_results=3) for q in queries]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in search_results:
            if isinstance(result, list):
                all_results.extend(result)

        unique_results = self._deduplicate(all_results)
        return WebResearchContext(
            query=question[:100],
            results=unique_results[:MAX_RESULTS],
            summary=self._build_summary(unique_results[:MAX_RESULTS]),
        )

    def _deduplicate(self, results: list[WebSearchResult]) -> list[WebSearchResult]:
        """Remove duplicate results by URL."""
        seen_urls = set()
        unique = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)
        return unique

    def _extract_company_names(self, doc_names: list[str]) -> list[str]:
        """Extract likely company names from document filenames."""
        companies = []
        for name in doc_names:
            clean = re.sub(r'\.(pdf|docx?|txt|xlsx?)$', '', name, flags=re.IGNORECASE)
            clean = re.sub(
                r'(sustainability|report|annual|esg|2024|2025|2023|_|-|copy|\d+)',
                ' ', clean, flags=re.IGNORECASE,
            )
            clean = re.sub(r'\s+', ' ', clean).strip()
            if clean and len(clean) > 2:
                companies.append(clean)
        return companies

    def _build_summary(self, results: list[WebSearchResult]) -> str:
        """Build a concise summary from search results."""
        if not results:
            return ""
        lines = ["WEB RESEARCH FINDINGS:"]
        for i, r in enumerate(results, 1):
            source_info = f" ({r.source})" if r.source else ""
            lines.append(f"{i}. [{r.title}]{source_info}")
            if r.snippet:
                lines.append(f"   {r.snippet[:200]}")
        return "\n".join(lines)

    def format_for_prompt(self, context: WebResearchContext) -> str:
        """Format web research results for inclusion in an LLM prompt."""
        if not context.results:
            return ""
        lines = [
            "\n--- REAL-TIME WEB RESEARCH (external sources for cross-reference) ---",
            f"Search: {context.query[:80]}",
            "",
        ]
        for i, r in enumerate(context.results, 1):
            lines.append(f"[{i}] {r.title}")
            if r.source:
                lines.append(f"    Source: {r.source}")
            if r.snippet:
                lines.append(f"    Info: {r.snippet[:250]}")
            lines.append("")
        lines.append(
            "NOTE: Use web research to CROSS-REFERENCE document claims. "
            "Cite as 'Web source:' when referencing. "
            "Document evidence always takes priority over web snippets."
        )
        lines.append("--- END WEB RESEARCH ---\n")
        return "\n".join(lines)
