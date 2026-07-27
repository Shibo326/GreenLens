---
name: greenlens-backend-hardening
description: Adds production-grade improvements to the GreenLens backend including AMD swap validation, benchmark endpoint, improved error messages, request ID logging, and deployment configuration files. Use this agent to harden the backend before deployment. Run after basic functionality is confirmed working.
tools: ["read", "write"]
---

You are the GreenLens Backend Hardening specialist. Your job is to add production-grade features to the backend without breaking any existing functionality.

## Pre-Work: Read Everything First

Before making any changes, read ALL of these files:
1. `backend/main.py`
2. `backend/services/llm_service.py`
3. `backend/services/analysis_service.py`
4. `backend/services/conflict_engine.py`
5. `backend/services/session_manager.py`
6. `backend/services/embedding_service.py`
7. `backend/routers/upload.py`
8. `backend/routers/chat.py`
9. `backend/routers/analyze.py`
10. `backend/routers/report.py`
11. `backend/.env.example`

Document the current state before making changes. Never skip the reading step.

---

## TASK 1: AMD Environment Validation in `llm_service.py`

In the `LLMService.__init__` method, add validation when `LLM_PROVIDER=AMD`:

```python
import logging
logger = logging.getLogger(__name__)

# Inside __init__, after reading env vars:
if self.provider.upper() == "AMD":
    if not os.getenv("AMD_CLOUD_ENDPOINT"):
        raise ValueError(
            "AMD_CLOUD_ENDPOINT is required when LLM_PROVIDER=AMD. "
            "Set it in your .env file or Railway environment variables."
        )
    if not os.getenv("AMD_CLOUD_API_KEY"):
        raise ValueError(
            "AMD_CLOUD_API_KEY is required when LLM_PROVIDER=AMD. "
            "Set it in your .env file or Railway environment variables."
        )
    logger.info(f"AMD Provider configured: endpoint={os.getenv('AMD_CLOUD_ENDPOINT')[:30]}...")
    logger.info(f"AMD Model: {self.model}")
```

---

## TASK 2: Add `GET /api/provider-info` Endpoint in `main.py`

Add this endpoint after the existing health check:

```python
@app.get("/api/provider-info")
async def provider_info():
    """Returns current LLM provider configuration (safe, no secrets)."""
    import os
    provider = os.getenv("LLM_PROVIDER", "GROQ").upper()
    return {
        "provider": provider,
        "isAMD": provider == "AMD",
        "model": os.getenv("AMD_MODEL", os.getenv("GROQ_MODEL", "unknown")),
        "endpoint": os.getenv("AMD_CLOUD_ENDPOINT", "")[:40] + "..." if os.getenv("AMD_CLOUD_ENDPOINT") else None,
    }
```

---

## TASK 3: Add `POST /api/benchmark` Endpoint in `routers/analyze.py`

Add a benchmark endpoint that times embedding of 50 test chunks:

```python
import time

@router.post("/benchmark")
async def benchmark_embeddings():
    """Benchmarks embedding performance with 50 test chunks."""
    embedding_service = _embedding_service  # injected from main.py at startup
    
    test_chunks = [
        f"This is test clause number {i} for benchmarking embedding performance in the GreenLens system."
        for i in range(50)
    ]
    
    start_time = time.time()
    try:
        embeddings = embedding_service.embed_batch(test_chunks)
        elapsed = time.time() - start_time
        return {
            "status": "success",
            "chunks_processed": len(test_chunks),
            "total_time_seconds": round(elapsed, 3),
            "avg_time_per_chunk_ms": round((elapsed / len(test_chunks)) * 1000, 2),
            "chunks_per_second": round(len(test_chunks) / elapsed, 1),
            "provider": os.getenv("LLM_PROVIDER", "GROQ"),
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 3),
        }
```

Note: The embedding service instance `_embedding_service` is injected into the analyze router module from `main.py` at startup — add it alongside the existing service references.

---

## TASK 4: Improve Error Response Format Across All Routers

All error responses must include three fields: `error`, `code`, and `suggestion`.

Update error responses in `upload.py`, `analyze.py`, `chat.py`, and `report.py`.

### Pattern to follow:
```python
# Instead of:
raise HTTPException(status_code=400, detail="Invalid file type")

# Use:
raise HTTPException(
    status_code=400,
    detail={
        "error": "Invalid file type",
        "code": "INVALID_FILE_TYPE",
        "suggestion": "Please upload PDF or image files only (PDF, PNG, JPG, JPEG, TIFF)."
    }
)
```

### Required error codes by router:

**upload.py:**
- `INVALID_FILE_TYPE` — unsupported mime type
- `FILE_TOO_LARGE` — file exceeds size limit
- `TOO_MANY_FILES` — more than allowed number of files
- `UPLOAD_FAILED` — generic upload failure
- `SESSION_NOT_FOUND` — session ID doesn't exist

**analyze.py:**
- `SESSION_NOT_FOUND` — session not found
- `NO_DOCUMENTS` — no documents in session to analyze
- `ANALYSIS_FAILED` — LLM or processing failure
- `BENCHMARK_FAILED` — benchmark endpoint failure

**chat.py:**
- `SESSION_NOT_FOUND` — session not found
- `NO_ANALYSIS` — analysis not complete yet
- `EMPTY_MESSAGE` — empty question submitted
- `STREAM_FAILED` — streaming failure

**report.py:**
- `SESSION_NOT_FOUND` — session not found
- `NO_ANALYSIS` — no analysis to export
- `PDF_GENERATION_FAILED` — PDF creation failure

---

## TASK 5: Improve `/health` Endpoint in `main.py`

Replace the existing health endpoint with:

```python
from datetime import datetime, timezone
import os

@app.get("/health")
async def health_check():
    provider = os.getenv("LLM_PROVIDER", "GROQ").upper()
    return {
        "status": "healthy",
        "service": "greenlens-api",
        "version": "1.0.0",
        "provider": provider,
        "amd_active": provider == "AMD",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

---

## TASK 6: Add Request ID Middleware in `main.py`

Add UUID-based request ID to every request for tracing:

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)
```

Add this middleware BEFORE other middleware registrations in `main.py`.

---

## TASK 7: Move Loose Test Files

Move these files from `backend/` root to `backend/tests/`:
- `test_groq.py` → `backend/tests/test_groq.py`
- `test_pipeline.py` → `backend/tests/test_pipeline.py` (if exists)
- `test_quick.py` → `backend/tests/test_quick.py` (if exists)
- `test_direct_groq.py` → `backend/tests/test_direct_groq.py`
- `test_full_flow.py` → `backend/tests/test_full_flow.py`

For each file: read the original, write it to the new location, then delete the original.

---

## TASK 8: Create `railway.toml` at Repo Root

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[environments.production.variables]
PYTHON_VERSION = "3.11"
```

---

## TASK 9: Create `README.md` at Repo Root

Create a comprehensive README:

```markdown
# GreenLens — AI Contract Intelligence

> Built for the AMD Hackathon on lablab.ai | Powered by AMD Cloud Inference

GreenLens analyzes legal contracts using AMD's high-performance AI inference. Upload multiple documents, detect conflicts between clauses, get risk assessments, and chat with your contracts using natural language.

## AMD Integration

This project leverages AMD Cloud endpoints for:
- **LLM Inference**: Contract analysis, risk assessment, chat responses
- **Embeddings**: Semantic search across contract clauses
- **Performance**: Full analysis in under 15s on AMD vs ~30s on standard providers

Switch between AMD (production) and Groq (testing) via `LLM_PROVIDER` env var.

## Features

- 📄 **Multi-document upload** — PDF, PNG, JPG, TIFF
- ⚡ **Conflict detection** — Cross-document clause comparison
- 🔍 **Risk analysis** — Severity-scored risk identification
- 💬 **Contract chat** — Streaming Q&A with evidence citations
- 📊 **PDF export** — Full analysis reports
- 🎯 **Demo mode** — Pre-loaded contracts for instant exploration

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | Python + FastAPI + uvicorn |
| LLM (prod) | AMD Cloud Inference |
| LLM (dev) | Groq API |
| Embeddings | sentence-transformers |
| PDF | ReportLab |
| Deployment | Railway (backend) + Vercel (frontend) |

## Quick Start

### Backend
```bash
cd backend
cp .env.example .env
# Fill in AMD_CLOUD_API_KEY and AMD_CLOUD_ENDPOINT (or GROQ_API_KEY for dev)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

### Both at once
```bash
./start_local.sh
```

## Environment Variables

### Backend (`.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `AMD` or `GROQ` |
| `AMD_CLOUD_ENDPOINT` | If AMD | AMD inference endpoint URL |
| `AMD_CLOUD_API_KEY` | If AMD | AMD API key |
| `GROQ_API_KEY` | If Groq | Groq API key (for dev/testing) |

### Frontend (`.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL |

## Running Tests

```bash
cd backend
./run_tests.sh   # Forces LLM_PROVIDER=GROQ, never uses AMD credits
```

## Deployment

- **Backend**: Deploy to Railway — `railway.toml` is pre-configured
- **Frontend**: Deploy to Vercel — `frontend/vercel.json` is pre-configured

## Team

Built with ❤️ for the AMD Hackathon on lablab.ai.

## License

MIT
```

---

## Completion Rules

- Show each complete modified file after every task
- Do not skip any task — all 9 must be completed
- If a file doesn't exist (e.g., test_pipeline.py), note it and skip gracefully
- Never break existing endpoints or functionality
- All new code must follow the existing code style in each file
