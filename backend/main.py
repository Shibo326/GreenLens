"""
GreenLens AI Backend — FastAPI Application
AMD MI300X-powered greenwashing detection service.
"""

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---- Import routers ----
from routers import upload, analyze, chat, report, demo, quick_scan
from routers import training, evaluation, prompts, feedback

# ---- Rate Limiter ----
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ---- Create FastAPI app ----
app = FastAPI(
    title="GreenLens AI",
    version="1.0.0",
    description="AMD MI300X-powered greenwashing and sustainability-claims detection API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---- Request ID Middleware ----
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)

# ---- GZip Compression ----
# Compress responses > 500 bytes — major win for JSON analysis payloads (often 10-30KB)
app.add_middleware(GZipMiddleware, minimum_size=500)

# ---- CORS Middleware ----
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
base_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
if allowed_origins_env:
    extra = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    allowed_origins = list(set(base_origins + extra))
else:
    allowed_origins = ["*"]

app.state.limiter = limiter

async def _custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "Too many requests. Please wait a moment before trying again.",
            "code": "RATE_LIMITED",
            "suggestion": f"You've exceeded the rate limit. Please retry after {exc.retry_after}.",
        },
    )

app.add_exception_handler(RateLimitExceeded, _custom_rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Cache-Control"],
)

# ---- Register Routers ----
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(report.router, prefix="/api", tags=["report"])
app.include_router(demo.router, prefix="/api", tags=["demo"])
app.include_router(quick_scan.router, prefix="/api", tags=["quick-scan"])
app.include_router(training.router, prefix="/api", tags=["training"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
app.include_router(prompts.router, prefix="/api", tags=["prompts"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])

# ---- Service Readiness Flag ----
app.state.services_ready = False


# ---- Global Exception Handler ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler.
    Logs the full traceback server-side but never exposes it in the response.
    """
    logger.exception(f"Unhandled exception for {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred.",
            "code": "UNKNOWN_ERROR",
            "suggestion": "Please try again. If the problem persists, contact support.",
        },
    )


# ---- Health Check ----
@app.get("/health", tags=["health"])
@app.head("/health", tags=["health"])
async def health_check():
    """Health check endpoint with provider and timestamp info. Supports GET and HEAD."""
    ready = getattr(app.state, "services_ready", False)
    status_code = 200 if ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if ready else "degraded",
            "service": "greenlens-api",
            "version": "1.0.0",
            "provider": "fireworks",
            "model": os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ready": ready,
        },
    )


@app.get("/api/provider-info", tags=["health"])
async def provider_info():
    """Returns current LLM provider configuration (safe, no secrets)."""
    endpoint = os.getenv("FIREWORKS_ENDPOINT", "")
    return {
        "provider": "fireworks",
        "isAMD": True,
        "model": os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b"),
        "endpoint": endpoint[:40] + "..." if endpoint else None,
    }


# ---- Self-Ping Keep-Alive ----
SELF_PING_INTERVAL = int(os.getenv("SELF_PING_INTERVAL", "120"))  # seconds (default 2 min)
_keep_alive_task: asyncio.Task | None = None


async def _self_ping_loop():
    """Background loop that pings our own /health endpoint to prevent Railway cold sleep."""
    # Determine the public URL (Railway sets RAILWAY_PUBLIC_DOMAIN or PORT)
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    port = int(os.getenv("PORT", "8000"))

    if public_domain:
        url = f"https://{public_domain}/health"
    else:
        # Local dev — ping localhost
        url = f"http://127.0.0.1:{port}/health"

    logger.info(f"Keep-alive self-ping started → {url} every {SELF_PING_INTERVAL}s")

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(SELF_PING_INTERVAL)
            try:
                resp = await client.get(url)
                logger.debug(f"Self-ping: {resp.status_code}")
            except Exception as e:
                logger.warning(f"Self-ping failed (non-fatal): {e}")


# ---- Startup Event ----
@app.on_event("startup")
async def startup_event():
    """
    Initialize all services at startup and inject into router modules.
    """
    global _keep_alive_task
    logger.info("GreenLens AI Backend starting up...")
    logger.info("AMD MI300X-powered greenwashing detection")

    # Start keep-alive background task
    _keep_alive_task = asyncio.create_task(_self_ping_loop())

    try:
        from services.document_parser import DocumentParser
        from services.embedding_service import EmbeddingService
        from services.vector_store import VectorStore
        from services.session_manager import SessionManager
        from services.llm_service import LLMService
        from services.conflict_engine import ConflictEngine
        from services.analysis_service import AnalysisService
        from services.pdf_generator import PDFGenerator
        from services.web_research import WebResearchService

        document_parser = DocumentParser()
        logger.info("DocumentParser initialized")

        embedding_service = EmbeddingService()
        logger.info("EmbeddingService initialized (all-MiniLM-L6-v2)")

        # Warm the embedding model
        try:
            _ = embedding_service.embed("warmup greenlens ai amd mi300x")
            logger.info("Embedding model warmed up")
        except Exception as warm_err:
            logger.warning(f"Warmup failed (non-fatal): {warm_err}")

        vector_store = VectorStore()
        logger.info("VectorStore initialized (ChromaDB in-memory)")

        session_manager = SessionManager()
        logger.info("SessionManager initialized")

        llm_service = LLMService()
        logger.info("LLMService initialized (Fireworks/AMD)")

        conflict_engine = ConflictEngine(llm_service)
        logger.info("ConflictEngine initialized")

        web_research = WebResearchService()
        logger.info("WebResearchService initialized (real-time web data)")

        analysis_service = AnalysisService(llm_service, conflict_engine, session_manager, web_research)
        logger.info("AnalysisService initialized")

        pdf_generator = PDFGenerator()
        logger.info("PDFGenerator initialized")

        from services.docx_generator import DOCXGenerator
        docx_generator = DOCXGenerator()
        logger.info("DOCXGenerator initialized")

        # Store llm_service globally for shutdown hook
        app.state.llm_service = llm_service
        app.state.web_research = web_research

        # --- Inject services into routers ---
        upload._document_parser = document_parser
        upload._embedding_service = embedding_service
        upload._vector_store = vector_store
        upload._session_manager = session_manager

        analyze._analysis_service = analysis_service
        analyze._session_manager = session_manager
        analyze._vector_store = vector_store
        analyze._embedding_service = embedding_service

        chat._embedding_service = embedding_service
        chat._vector_store = vector_store
        chat._session_manager = session_manager
        chat._llm_service = llm_service
        chat._web_research = web_research

        report._pdf_generator = pdf_generator
        report._docx_generator = docx_generator
        report._session_manager = session_manager

        quick_scan._llm_service = llm_service
        quick_scan._web_research = web_research

        # --- Inject services into AI Advanced Training routers ---
        from services.training_pipeline import TrainingPipelineService
        from services.evaluation_framework import EvaluationFramework
        from services.prompt_optimizer import PromptOptimizer

        training_pipeline_svc = TrainingPipelineService()
        logger.info("TrainingPipelineService initialized")

        evaluation_framework = EvaluationFramework(
            llm_service=llm_service,
            training_pipeline=training_pipeline_svc,
        )
        logger.info("EvaluationFramework initialized")

        prompt_optimizer = PromptOptimizer(evaluation_framework=evaluation_framework)
        logger.info("PromptOptimizer initialized")

        evaluation._evaluation_framework = evaluation_framework
        prompts._prompt_optimizer = prompt_optimizer

        logger.info("All services initialized — GreenLens AI is ready!")

        # Mark app as ready
        app.state.services_ready = True

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        logger.exception("Startup exception details:")
        app.state.services_ready = False


# ---- Shutdown Event ----
@app.on_event("shutdown")
async def shutdown_event():
    """Close persistent HTTP connections and cancel background tasks on graceful shutdown."""
    global _keep_alive_task
    logger.info("GreenLens AI Backend shutting down...")

    # Cancel keep-alive task
    if _keep_alive_task and not _keep_alive_task.done():
        _keep_alive_task.cancel()
        logger.info("Keep-alive task cancelled")

    if hasattr(app.state, "llm_service"):
        try:
            await app.state.llm_service.aclose()
            logger.info("LLMService HTTP client closed")
        except Exception as e:
            logger.warning(f"LLMService cleanup failed (non-fatal): {e}")

    if hasattr(app.state, "web_research"):
        try:
            await app.state.web_research.aclose()
            logger.info("WebResearchService HTTP client closed")
        except Exception as e:
            logger.warning(f"WebResearchService cleanup failed (non-fatal): {e}")


# ---- Entry Point ----
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
