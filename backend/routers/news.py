"""
GreenLens News Router — Greenwashing news feed via DuckDuckGo search.

Provides a GET /api/news endpoint that returns recent greenwashing news articles
with live search, 30-minute caching, and a curated fallback list.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ---- Response Models ----

class NewsArticle(BaseModel):
    title: str
    url: str
    snippet: str
    source: str  # domain name like "bbc.com"
    category: str = "greenwashing"  # greenwashing, regulation, enforcement


class NewsResponse(BaseModel):
    articles: list[NewsArticle]
    lastUpdated: str  # ISO timestamp
    source: str  # "live" or "cached" or "curated"


# ---- In-Memory Cache ----
_cache: dict = {
    "articles": [],
    "timestamp": 0.0,
    "source": "",
}
_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


# ---- Search Queries ----
_SEARCH_QUERIES = [
    "greenwashing news 2024 2025",
    "company greenwashing fined",
    "sustainability fraud corporate",
]


# ---- Curated Fallback Articles ----
_CURATED_ARTICLES: list[NewsArticle] = [
    NewsArticle(
        title="H&M faces lawsuit over greenwashing claims on clothing labels",
        url="https://www.bbc.com/news/business-62240314",
        snippet="H&M is facing a lawsuit in the US over claims that environmental scorecards on its products are misleading, constituting greenwashing.",
        source="bbc.com",
        category="enforcement",
    ),
    NewsArticle(
        title="Shell and BP ads banned for greenwashing by UK regulator",
        url="https://www.theguardian.com/business/2023/jun/14/shell-bp-ads-banned-greenwashing-uk-regulator",
        snippet="The UK Advertising Standards Authority banned ads from Shell and BP for giving a misleading impression of the companies' environmental efforts.",
        source="theguardian.com",
        category="enforcement",
    ),
    NewsArticle(
        title="EU agrees ban on greenwashing and misleading product labels",
        url="https://www.reuters.com/sustainability/eu-agrees-ban-greenwashing-misleading-product-labels-2024-01-17/",
        snippet="European Union lawmakers approved a directive banning generic environmental claims like 'eco-friendly' or 'green' without proof.",
        source="reuters.com",
        category="regulation",
    ),
    NewsArticle(
        title="Keurig to pay $3 million for misleading recyclability claims",
        url="https://www.ftc.gov/news-events/news/press-releases/2022/01/keurig-canada-pay-3-million-penalty-misleading-recyclability-claims",
        snippet="Keurig Canada agreed to pay a $3 million penalty for making false or misleading claims that its single-use K-Cup pods could be recycled.",
        source="ftc.gov",
        category="enforcement",
    ),
    NewsArticle(
        title="Volkswagen emissions scandal: how it unfolded",
        url="https://www.nytimes.com/2017/05/06/business/volkswagen-emissions-scandal.html",
        snippet="Volkswagen admitted to installing software in diesel vehicles to cheat emissions tests, affecting 11 million cars worldwide in one of the largest corporate frauds.",
        source="nytimes.com",
        category="greenwashing",
    ),
    NewsArticle(
        title="SEC charges Goldman Sachs asset management for ESG greenwashing",
        url="https://www.cnbc.com/2022/11/22/sec-fines-goldman-sachs-4-million-over-esg-fund-claims.html",
        snippet="Goldman Sachs was fined $4 million by the SEC for failing to follow its own ESG policies and procedures in its mutual funds and separately managed accounts.",
        source="cnbc.com",
        category="enforcement",
    ),
    NewsArticle(
        title="DWS ex-CEO charged over greenwashing allegations at Deutsche Bank unit",
        url="https://www.reuters.com/business/finance/germanys-dws-ex-ceo-charged-over-greenwashing-allegations-2023-05-31/",
        snippet="The former CEO of Deutsche Bank's asset management arm DWS was charged with making misleading statements about ESG criteria in investment products.",
        source="reuters.com",
        category="enforcement",
    ),
    NewsArticle(
        title="ASIC sues Mercer for greenwashing over sustainable investment claims",
        url="https://www.theguardian.com/australia-news/2023/feb/28/asic-sues-mercer-super-for-greenwashing-over-sustainable-investment-options",
        snippet="Australia's corporate regulator ASIC sued Mercer Superannuation for making misleading claims about the sustainability of some of its investment options.",
        source="theguardian.com",
        category="enforcement",
    ),
    NewsArticle(
        title="TotalEnergies accused of major greenwashing in landmark French case",
        url="https://www.theguardian.com/environment/2023/mar/02/totalenergies-accused-greenwashing-landmark-french-case",
        snippet="Environmental groups filed a legal complaint against TotalEnergies for allegedly misleading consumers with claims about its climate commitments.",
        source="theguardian.com",
        category="greenwashing",
    ),
    NewsArticle(
        title="Airlines face greenwashing crackdown over carbon offset claims",
        url="https://www.bbc.com/news/science-environment-67074917",
        snippet="Airlines are under increased scrutiny for selling carbon offsets that environmental groups say do little to reduce actual emissions from flights.",
        source="bbc.com",
        category="regulation",
    ),
]


def _extract_domain(url: str) -> str:
    """Extract a clean domain name from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.hostname or ""
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return "unknown"


def _categorize_article(title: str, snippet: str) -> str:
    """Assign a category based on keywords in title/snippet."""
    text = (title + " " + snippet).lower()
    if any(w in text for w in ["fine", "fined", "penalty", "lawsuit", "sued", "charged", "banned"]):
        return "enforcement"
    if any(w in text for w in ["regulation", "directive", "law", "ban", "rule", "policy", "crackdown"]):
        return "regulation"
    return "greenwashing"


async def _fetch_live_articles() -> list[NewsArticle]:
    """Fetch live articles from DuckDuckGo search. Returns empty list on failure."""
    try:
        from services.web_search import _execute_search
    except ImportError:
        logger.warning("[news] Could not import web_search module")
        return []

    articles: list[NewsArticle] = []
    seen_urls: set[str] = set()

    for query in _SEARCH_QUERIES:
        try:
            results = await asyncio.wait_for(
                _execute_search(query, max_results=5),
                timeout=5,
            )
            for result in results:
                url = result.get("href", "").strip()
                title = result.get("title", "").strip()
                snippet = result.get("body", "").strip()

                if not url or not title or url in seen_urls:
                    continue
                seen_urls.add(url)

                if len(snippet) > 300:
                    snippet = snippet[:297] + "..."

                domain = _extract_domain(url)
                category = _categorize_article(title, snippet)

                articles.append(NewsArticle(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=domain,
                    category=category,
                ))
        except asyncio.TimeoutError:
            logger.warning(f"[news] Timeout fetching results for: {query}")
        except Exception as e:
            logger.warning(f"[news] Error fetching results for {query}: {e}")

    return articles


# ---- Endpoint ----

@router.get("/news", response_model=NewsResponse)
async def get_news():
    """
    Returns recent greenwashing news articles.

    - Searches DuckDuckGo for live results
    - Caches results for 30 minutes
    - Falls back to curated list if search fails
    """
    global _cache

    # Check cache validity
    now = time.time()
    if _cache["articles"] and (now - _cache["timestamp"]) < _CACHE_TTL_SECONDS:
        return NewsResponse(
            articles=_cache["articles"],
            lastUpdated=datetime.fromtimestamp(_cache["timestamp"], tz=timezone.utc).isoformat(),
            source="cached",
        )

    # Try live search
    articles = await _fetch_live_articles()

    if articles:
        _cache["articles"] = articles
        _cache["timestamp"] = now
        _cache["source"] = "live"
        return NewsResponse(
            articles=articles,
            lastUpdated=datetime.now(timezone.utc).isoformat(),
            source="live",
        )

    # Fallback to curated list
    logger.info("[news] Using curated fallback articles")
    return NewsResponse(
        articles=_CURATED_ARTICLES,
        lastUpdated=datetime.now(timezone.utc).isoformat(),
        source="curated",
    )
