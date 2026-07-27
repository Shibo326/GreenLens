import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.response import QuickScanRequest, QuickScanResponse
from prompts.quick_scan import build_quick_scan_prompt
from services.llm_service import LLMService, _strip_json_fences
from services.web_research import WebResearchService

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

# Service instances (set from main.py at startup)
_llm_service: LLMService | None = None
_web_research: WebResearchService | None = None


def _err(status: int, message: str, code: str, suggestion: str = ""):
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


@router.post("/quick-scan")
@limiter.limit("10/minute")
async def quick_scan(request: Request, body: QuickScanRequest):
    """
    Instant single-claim greenwashing verdict — no document upload required.

    Accepts a marketing/sustainability claim (max 500 chars) and returns
    a verdict, what to look for, and confidence level.
    """
    llm_service = _llm_service

    if llm_service is None:
        return _err(
            503,
            "Service is starting up. Please try again in a moment.",
            "SERVICE_UNAVAILABLE",
            "The server is still initializing. Please retry in 10-20 seconds.",
        )

    claim = body.claim

    # --- Validate claim ---
    if not claim or not claim.strip():
        return _err(
            422,
            "Claim text is required.",
            "INVALID_REQUEST",
            "Please enter a sustainability or marketing claim to scan.",
        )

    if len(claim) > 500:
        return _err(
            422,
            "Claim too long. Maximum 500 characters.",
            "INVALID_REQUEST",
            "Please shorten the claim to 500 characters or fewer.",
        )

    # --- Build prompt and call LLM ---
    # --- Web Research: fetch online data about this claim ---
    web_context_str = ""
    if _web_research:
        try:
            web_ctx = await _web_research.research_claim(claim.strip())
            web_context_str = _web_research.format_for_prompt(web_ctx)
            if web_context_str:
                logger.info(f"[quick-scan] Web research enriched with {len(web_ctx.results)} results")
        except Exception as web_err:
            logger.warning(f"[quick-scan] Web research failed (non-fatal): {web_err}")

    user_prompt = build_quick_scan_prompt(claim.strip(), web_context=web_context_str)
    system_prompt = (
        "You are a sustainability claims analyst specializing in greenwashing detection. "
        "You have access to real-time web research to cross-reference claims. "
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
            # Fallback: return a generic response
            logger.warning(f"[quick-scan] JSON parse failed. Raw: {raw[:300]!r}")
            data = {
                "verdict": "Unable to parse AI response. Please try rephrasing your claim.",
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
        logger.error(f"[quick-scan] LLM error: {e}", exc_info=True)
        return _err(
            502,
            f"Quick scan failed: {type(e).__name__}",
            "ANALYSIS_FAILED",
            "The AI service encountered an error. Please try again.",
        )
