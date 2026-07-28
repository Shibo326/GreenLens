import logging
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models.response import AnalyzeRequest, AnalyzeResponse
from services.analysis_service import AnalysisService
from services.embedding_service import EmbeddingService
from services.llm_service import LLMParseError, LLMRateLimitError
from services.session_manager import SessionManager, SessionNotFoundError
from services.vector_store import VectorStore
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances (set from main.py at startup)
_analysis_service: AnalysisService | None = None
_session_manager: SessionManager | None = None
_vector_store: VectorStore | None = None
_embedding_service: EmbeddingService | None = None


def _err(status: int, message: str, code: str, suggestion: str = ""):
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


def _check_services():
    """Return an error response if services are not initialized, or None if ready."""
    if _analysis_service is None or _session_manager is None or _vector_store is None:
        return _err(503, "Service is starting up. Please try again in a moment.", "SERVICE_UNAVAILABLE", "The server is still initializing. Please retry in 10-20 seconds.")
    return None


@router.post("/suggest-questions")
@limiter.limit("10/minute")
async def suggest_questions(request: Request, body: AnalyzeRequest):
    """
    Generate contextually-relevant quick questions based on the uploaded documents.
    Returns 6 short questions adapted to the document type and content.
    """
    svc_err = _check_services()
    if svc_err:
        return svc_err

    session_manager = _session_manager
    vector_store = _vector_store
    analysis_service = _analysis_service

    session_id = body.sessionId

    # --- Validate session ---
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        return _err(404, "Session not found.", "SESSION_NOT_FOUND", "Please upload documents first to create a session.")

    # --- Cache check: return cached questions if analysis already completed ---
    if session.analysis is not None and session.analysis.suggestedQuestions:
        logger.info(f"Returning cached questions for session {session_id}")
        return JSONResponse(content={"questions": session.analysis.suggestedQuestions})

    # --- Retrieve chunks ---
    chunks = vector_store.get_all_chunks(session_id)

    if not chunks:
        return JSONResponse(content={"questions": []})

    # --- Generate questions (uses the merged summary+questions call internally) ---
    try:
        from prompts.system_prompt import get_system_prompt
        doc_names = [c.source_document for c in chunks]
        doc_names = list(dict.fromkeys(doc_names))  # dedupe preserving order
        system_prompt = get_system_prompt(doc_names)
        _, questions = await analysis_service._generate_summary_and_questions(
            system_prompt, chunks
        )
    except Exception as e:
        logger.error(f"Question generation failed for session {session_id}: {e}")
        return JSONResponse(content={"questions": []})

    return JSONResponse(content={"questions": questions})


@router.get("/warmup")
async def warmup():
    """
    Lightweight wake-up endpoint — called by the frontend on page load to prevent
    Railway cold-start delays when the user clicks Analyze.
    Returns instantly; just having the server handle a request is enough to wake it.
    """
    return {"status": "warm", "service": "greenlens-api"}


@router.get("/diagnose")
async def diagnose_llm():
    """
    Diagnostic endpoint — tests each LLM model tier with a minimal prompt.
    Hit this from browser: https://your-railway-url/api/diagnose
    Returns which models work and which fail, with error details.
    """
    import os
    from services.llm_service import LLMService

    svc_err = _check_services()
    if svc_err:
        return svc_err

    results = {}
    llm = _analysis_service.llm_service

    tiers = {
        "premium": llm._model_premium,
        "quality": llm._model_quality,
        "fast": llm._model_fast,
    }

    for tier_name, model_id in tiers.items():
        try:
            response = await llm.complete(
                "You are a test assistant.",
                "Reply with exactly: OK",
                max_tokens=10,
                temperature=0.0,
                tier=tier_name,
            )
            results[tier_name] = {
                "status": "OK",
                "model": model_id,
                "response": response.strip()[:50],
            }
        except Exception as e:
            results[tier_name] = {
                "status": "FAILED",
                "model": model_id,
                "error": str(e)[:200],
            }

    # Summary
    working = [k for k, v in results.items() if v["status"] == "OK"]
    failed = [k for k, v in results.items() if v["status"] == "FAILED"]

    return {
        "summary": f"{len(working)}/3 models working",
        "working_tiers": working,
        "failed_tiers": failed,
        "endpoint": os.getenv("FIREWORKS_ENDPOINT", "")[:50],
        "api_key_set": bool(os.getenv("FIREWORKS_API_KEY")),
        "api_key_prefix": os.getenv("FIREWORKS_API_KEY", "")[:8] + "...",
        "details": results,
    }


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze_documents(request: Request, body: AnalyzeRequest):
    """
    Run full AI analysis on all documents in a session.
    Rate limited: 5 per IP per minute to protect Groq quota.

    Returns executive summary, risks, comparison matrix, conflicts, and recommendation.
    """
    analysis_service = _analysis_service
    session_manager = _session_manager
    vector_store = _vector_store

    svc_err = _check_services()
    if svc_err:
        return svc_err

    session_id = body.sessionId

    # --- Validate session ---
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        return _err(404, "Session not found.", "SESSION_NOT_FOUND", "Please upload documents first to create a session.")

    # --- Cache check: return existing analysis instantly if available (skip if force=true) ---
    if session.analysis is not None and not body.force:
        logger.info(f"Returning cached analysis for session {session_id} (0ms)")
        response = AnalyzeResponse(
            sessionId=session_id,
            status="completed",
            analysis=session.analysis,
        )
        return JSONResponse(content=response.model_dump(mode="json"))

    # --- Retrieve chunks ---
    chunks = vector_store.get_all_chunks(session_id)
    doc_names = [doc.filename for doc in session.documents]

    # --- Run analysis ---
    try:
        analysis = await analysis_service.run_full_analysis(
            session_id=session_id,
            chunks=chunks,
            doc_names=doc_names,
        )
    except LLMRateLimitError as e:
        logger.error(f"LLM rate limit hit for session {session_id}: {e}")
        return _err(429, "Analysis failed. API quota exceeded — please try again later or use a different API key.", "RATE_LIMIT_EXCEEDED", "Wait a minute and try again, or use a different API key.")
    except LLMParseError as e:
        logger.error(f"LLM parse error for session {session_id}: {e}")
        return _err(502, "Analysis failed. LLM service unavailable.", "ANALYSIS_FAILED", "The AI service is temporarily unavailable. Please try again shortly.")
    except Exception as e:
        # Also catch rate limit errors that may have been wrapped
        err_str = str(e).lower()
        if "rate_limit_exceeded" in err_str or "rate limit" in err_str or "429" in err_str:
            logger.error(f"LLM rate limit (wrapped) for session {session_id}: {e}")
            return _err(429, "Analysis failed. API quota exceeded — please try again later or use a different API key.", "RATE_LIMIT_EXCEEDED", "Wait a minute and try again, or use a different API key.")
        logger.error(f"Analysis failed for session {session_id}: {e}")
        return _err(502, "Analysis failed. LLM service unavailable.", "ANALYSIS_FAILED", "The AI service is temporarily unavailable. Please try again shortly.")

    response = AnalyzeResponse(
        sessionId=session_id,
        status="completed",
        analysis=analysis,
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@router.post("/benchmark")
async def benchmark_embeddings():
    """
    Benchmarks AMD MI300X embedding speed via Fireworks AI vs local CPU baseline.

    Runs 50 contract clause chunks through:
      1. Fireworks AI /v1/embeddings (AMD Instinct MI300X cloud)
      2. Local sentence-transformers CPU baseline

    Returns timing, ratio, and hardware info for demo purposes.
    Results are cached for 5 minutes to avoid excessive API calls.
    """
    import httpx
    import os

    # Server-side cache (5 min TTL)
    cache_ttl = 300
    if hasattr(benchmark_embeddings, "_cache") and benchmark_embeddings._cache:
        cached_at, cached_result = benchmark_embeddings._cache
        if time.time() - cached_at < cache_ttl:
            return JSONResponse(content=cached_result)

    embedding_service = _embedding_service

    test_chunks = [
        "Payment terms: Net 30 days from invoice date. Late payment incurs 1.5% monthly interest.",
        "Supplier warrants all goods for 24 months from delivery date.",
        "Total contract value: $142,500.00 USD, subject to annual CPI adjustment.",
        "Governing law: State of California, United States of America.",
        "Either party may terminate this agreement with 30 days written notice.",
        "Force majeure: Neither party liable for delays caused by events beyond reasonable control.",
        "Confidentiality obligations survive termination for a period of five (5) years.",
        "Intellectual property developed under this contract remains property of the client.",
        "Dispute resolution: binding arbitration under AAA Commercial Arbitration Rules.",
        "Indemnification: Supplier indemnifies Client against third-party IP infringement claims.",
    ] * 5  # 50 chunks total

    fireworks_key = os.getenv("FIREWORKS_API_KEY", "")
    fireworks_endpoint = os.getenv("FIREWORKS_ENDPOINT", "https://api.fireworks.ai/inference/v1")

    results = {}

    # --- AMD MI300X via Fireworks AI ---
    if fireworks_key:
        amd_start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{fireworks_endpoint}/embeddings",
                    headers={
                        "Authorization": f"Bearer {fireworks_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "nomic-ai/nomic-embed-text-v1.5",
                        "input": test_chunks,
                    },
                )
                response.raise_for_status()
            amd_elapsed = round(time.perf_counter() - amd_start, 3)
            results["amd_fireworks"] = {
                "hardware": "AMD Instinct MI300X via Fireworks AI",
                "model": "nomic-ai/nomic-embed-text-v1.5",
                "chunks_processed": len(test_chunks),
                "time_seconds": amd_elapsed,
                "chunks_per_second": round(len(test_chunks) / amd_elapsed, 1),
            }
        except Exception as e:
            results["amd_fireworks"] = {"error": str(e)[:120]}
    else:
        results["amd_fireworks"] = {"error": "FIREWORKS_API_KEY not configured"}

    # --- Local CPU baseline (sentence-transformers) ---
    if embedding_service is not None:
        cpu_start = time.perf_counter()
        try:
            embedding_service.embed_batch(test_chunks)
            cpu_elapsed = round(time.perf_counter() - cpu_start, 3)
            results["cpu_baseline"] = {
                "hardware": "CPU (sentence-transformers all-MiniLM-L6-v2)",
                "model": "all-MiniLM-L6-v2",
                "chunks_processed": len(test_chunks),
                "time_seconds": cpu_elapsed,
                "chunks_per_second": round(len(test_chunks) / cpu_elapsed, 1),
            }
        except Exception as e:
            results["cpu_baseline"] = {"error": str(e)[:120]}
    else:
        results["cpu_baseline"] = {"error": "EmbeddingService not initialized"}

    # --- Compute speedup ratio ---
    speedup_ratio = None
    if (
        "time_seconds" in results.get("amd_fireworks", {})
        and "time_seconds" in results.get("cpu_baseline", {})
    ):
        cpu_t = results["cpu_baseline"]["time_seconds"]
        amd_t = results["amd_fireworks"]["time_seconds"]
        if amd_t > 0:
            speedup_ratio = round(cpu_t / amd_t, 2)

    result = {
        "status": "success",
        "benchmark": results,
        "speedup_ratio": speedup_ratio,
        "speedup_label": f"{speedup_ratio}x faster on AMD MI300X" if speedup_ratio else None,
        "note": "AMD MI300X benchmark via Fireworks AI embeddings endpoint",
    }

    # Cache the result
    benchmark_embeddings._cache = (time.time(), result)

    return result
