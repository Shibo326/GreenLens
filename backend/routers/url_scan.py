"""
URL Scanner endpoint — fetch a web page, extract text, and run greenwashing analysis.
"""

import json
import logging
import re
from html.parser import HTMLParser

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.response import QuickScanResponse
from services.llm_service import LLMService, _strip_json_fences

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Service instances (set from main.py at startup)
_llm_service: LLMService | None = None


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class UrlScanRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# HTML text extraction
# ---------------------------------------------------------------------------


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML-to-text extractor using stdlib html.parser."""

    _skip_tags = frozenset(["script", "style", "noscript", "svg", "head"])

    def __init__(self):
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth == 0:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = " ".join(self._pieces)
        # Normalize whitespace
        return re.sub(r"\s+", " ", raw).strip()


def _extract_text_from_html(html: str) -> str:
    """Extract visible text from HTML content."""
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        # Fallback: strip tags with regex
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()
    return extractor.get_text()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(status: int, message: str, code: str, suggestion: str = ""):
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


def _build_url_scan_prompt(page_text: str, url: str) -> str:
    """Build a prompt for analyzing web page content for greenwashing."""
    return f"""You are a sustainability claims analyst specializing in greenwashing detection. A user has provided a web page URL and we have extracted its text content. Analyze the page for greenwashing claims.

URL: {url}

PAGE CONTENT (extracted text):
\"\"\"
{page_text}
\"\"\"

Evaluate:
1. Does this page contain sustainability or environmental marketing claims?
2. Are claims specific and measurable, or vague and unverifiable ("eco-friendly", "green", "natural")?
3. Do they reference specific standards, certifications, or measurable targets?
4. Are there any contradictions or red flags typical of greenwashing?
5. Is the language designed to mislead consumers about environmental impact?

Return ONLY valid JSON:
{{
  "verdict": "<2-3 sentence assessment of the greenwashing risk on this page — what claims are made, what's suspicious or credible, and an overall assessment>",
  "whatToLookFor": ["<specific thing to verify>", "<specific thing to verify>", "<specific thing to verify>"],
  "confidence": "<LOW|MEDIUM|HIGH — how confident you are in this assessment>"
}}"""


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/url-scan")
@limiter.limit("5/minute")
async def url_scan(request: Request, body: UrlScanRequest):
    """
    Scan a URL for greenwashing claims.

    Fetches the page, extracts text, and runs LLM analysis to produce
    a Quick Scan-style verdict.
    """
    llm_service = _llm_service

    if llm_service is None:
        return _err(
            503,
            "Service is starting up. Please try again in a moment.",
            "SERVICE_UNAVAILABLE",
            "The server is still initializing. Please retry in 10-20 seconds.",
        )

    url = body.url.strip()

    # --- Validate URL ---
    if not url:
        return _err(
            422,
            "URL is required.",
            "INVALID_REQUEST",
            "Please enter a URL to scan.",
        )

    if len(url) > 2000:
        return _err(
            422,
            "URL too long. Maximum 2000 characters.",
            "INVALID_REQUEST",
            "Please provide a shorter URL.",
        )

    if not url.startswith("http://") and not url.startswith("https://"):
        return _err(
            422,
            "Invalid URL. Must start with http:// or https://.",
            "INVALID_REQUEST",
            "Please enter a valid URL starting with http:// or https://.",
        )

    # --- Fetch page content ---
    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, max_redirects=5
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "GreenLens-Bot/1.0 (greenwashing-scanner)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            resp.raise_for_status()
            html_content = resp.text
    except httpx.TimeoutException:
        return _err(
            502,
            "Timeout fetching the URL. The site took too long to respond.",
            "NETWORK_ERROR",
            "The target website didn't respond within 15 seconds. Try again or use a different URL.",
        )
    except httpx.HTTPStatusError as e:
        return _err(
            502,
            f"Failed to fetch URL: HTTP {e.response.status_code}",
            "NETWORK_ERROR",
            "The target website returned an error. Check the URL and try again.",
        )
    except Exception as e:
        logger.warning(f"[url-scan] Fetch error: {type(e).__name__}: {e}")
        return _err(
            502,
            f"Failed to fetch URL: {type(e).__name__}",
            "NETWORK_ERROR",
            "Could not reach the website. Check the URL and try again.",
        )

    # --- Extract text ---
    page_text = _extract_text_from_html(html_content)

    if not page_text or len(page_text) < 50:
        return _err(
            422,
            "Could not extract meaningful text from the page. It may be JavaScript-rendered or empty.",
            "INVALID_REQUEST",
            "Try a different URL with more static content.",
        )

    # Truncate to 5000 chars
    if len(page_text) > 5000:
        page_text = page_text[:5000]

    # --- Build prompt and call LLM ---
    user_prompt = _build_url_scan_prompt(page_text, url)
    system_prompt = (
        "You are a sustainability claims analyst specializing in greenwashing detection. "
        "Respond ONLY with valid JSON — no prose, no markdown fences."
    )

    try:
        raw = await llm_service.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=600,
            temperature=0.2,
            tier="fast",
        )
        raw = _strip_json_fences(raw)

        # Parse JSON with fallback
        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try extracting JSON object from response
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                try:
                    data = json.loads(raw[brace_start : brace_end + 1])
                except json.JSONDecodeError:
                    pass

        if data is None:
            logger.warning(f"[url-scan] JSON parse failed. Raw: {raw[:300]!r}")
            data = {
                "verdict": "Unable to parse AI response. Please try again.",
                "whatToLookFor": [
                    "Third-party certification",
                    "Specific measurable targets",
                    "Scope and boundary definitions",
                ],
                "confidence": "LOW",
            }

        # Validate and normalize confidence
        confidence = str(data.get("confidence", "MEDIUM")).upper()
        if confidence not in ("LOW", "MEDIUM", "HIGH"):
            confidence = "MEDIUM"

        # Ensure whatToLookFor is a list of strings
        what_to_look_for = data.get("whatToLookFor", [])
        if not isinstance(what_to_look_for, list):
            what_to_look_for = [str(what_to_look_for)]
        what_to_look_for = [str(item) for item in what_to_look_for if item]

        response = QuickScanResponse(
            verdict=str(data.get("verdict", "")),
            whatToLookFor=what_to_look_for,
            confidence=confidence,
        )
        return JSONResponse(content=response.model_dump(mode="json"))

    except Exception as e:
        logger.error(f"[url-scan] LLM error: {e}", exc_info=True)
        return _err(
            502,
            f"URL scan failed: {type(e).__name__}",
            "ANALYSIS_FAILED",
            "The AI service encountered an error. Please try again.",
        )
