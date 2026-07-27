# GreenLens AI — Greenwashing Detection Powered by AMD MI300X

> Upload sustainability reports and marketing materials → AI cross-references claims against data and flags contradictions, vague language, and unverified assertions in under 90 seconds.

**Live Demo:** https://amd-hackthon-ll14.vercel.app  
**Backend API:** https://amdhackthon-production.up.railway.app  
**GitHub:** https://github.com/your-repo/AmdHackthon  
**Track:** AI for Sustainability 🌱 — YFS Build for Good Hackathon

---

## What It Does

GreenLens analyzes a company's sustainability claims (reports, packaging, marketing) simultaneously and:

- 🔍 Detects **greenwashing contradictions** between what companies claim and what their own data shows
- 📊 Generates a **Greenwash Score (0–100)** — color-coded credibility gauge
- ⚖️ Builds a **Claim vs. Reality Matrix** comparing marketing language against reported data
- ⚡ **Quick Scan** — instant verdict on any sustainability claim, no documents needed
- 📷 **Snap & Check** — photograph product labels/packaging for AI vision analysis
- 💬 **Chat Copilot** — sustainability analyst persona with RAG-grounded citations
- 🧒 **ELI15 Mode** — toggle to simplify AI responses for younger audiences
- 🌐 **Bilingual** — responds in English and Filipino/Tagalog (language matching)
- 📄 Exports full analysis as **PDF or DOCX**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React 18 / Vite / TailwindCSS 4)  → Vercel  │
└────────────────────────┬────────────────────────────────┘
                         │ REST + SSE
┌────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI / Python 3.11)             → Railway  │
│  ├── RAG: ChromaDB + all-MiniLM-L6-v2 embeddings       │
│  ├── 5 parallel LLM calls via asyncio.gather            │
│  └── Semaphore(3) rate-limit protection                 │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────┐
│  Fireworks AI  (AMD Instinct MI300X hardware)           │
│  ├── deepseek-v4-flash  (quality tier — reasoning)     │
│  └── gpt-oss-120b       (fast tier — 646 tok/s)        │
└─────────────────────────────────────────────────────────┘
```

### AI Pipeline (5 parallel LLM calls)

| # | Task | Model | Tier |
|---|------|-------|------|
| 1 | Executive Summary + Greenwash Score | deepseek-v4-flash | Quality |
| 2 | Risk/Flag Analysis | deepseek-v4-flash | Quality |
| 3 | Claim vs. Reality Matrix | gpt-oss-120b | Fast (MI300X) |
| 4 | Accountability Action Steps | deepseek-v4-flash | Quality |
| 5 | Contradiction Detection | gpt-oss-120b | Fast (MI300X) |

All 5 run concurrently via `asyncio.gather` with `Semaphore(3)` to prevent rate-limit cascades.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Fireworks AI API key → https://app.fireworks.ai

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env — add your FIREWORKS_API_KEY
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
# Edit .env — set VITE_API_URL=http://localhost:8000
npm install
npm run dev
# → http://localhost:5173
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIREWORKS_API_KEY` | ✅ | — | Fireworks AI API key |
| `FIREWORKS_ENDPOINT` | ✅ | `https://api.fireworks.ai/inference/v1` | Fireworks API base URL |
| `FIREWORKS_MODEL_QUALITY` | — | `accounts/fireworks/models/deepseek-v4-flash` | Quality tier model (reasoning) |
| `FIREWORKS_MODEL_FAST` | — | `accounts/fireworks/models/gpt-oss-120b` | Fast tier model (MI300X optimized) |
| `FIREWORKS_MODEL_VISION` | — | *(disabled)* | Vision model for Snap & Check |
| `SINGLE_CALL_MODE` | — | `false` | Emergency: combine all analysis into 1 call |
| `ALLOWED_ORIGINS` | — | `*` (all) | Comma-separated CORS origins |
| `PORT` | — | `8000` | Server port |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | ✅ | Backend URL (e.g., `http://localhost:8000` or Railway URL) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload documents (PDF, PNG, JPEG, DOCX) — max 10 files, 10 MB each |
| `POST` | `/api/analyze` | Run full 5-call AI analysis pipeline |
| `POST` | `/api/suggest-questions` | Generate context-aware questions from documents |
| `POST` | `/api/quick-scan` | Instant greenwashing verdict on a single claim (no upload needed) |
| `POST` | `/api/chat` | RAG-powered Q&A about uploaded documents |
| `POST` | `/api/chat/stream` | Streaming chat via SSE (Server-Sent Events) |
| `POST` | `/api/chat/vision` | Snap & Check — analyze product label/packaging image |
| `POST` | `/api/report` | Export analysis as PDF or DOCX |
| `GET` | `/api/demo` | Pre-loaded demo data (EcoTech Corp greenwashing case) |
| `GET` | `/api/warmup` | Wake backend from cold start |
| `GET` | `/api/provider-info` | Current LLM provider config (no secrets) |
| `GET` | `/api/benchmark` | Live inference speed benchmark |
| `POST` | `/api/benchmark` | AMD MI300X embedding benchmark (CPU vs GPU comparison) |
| `GET` | `/api/session/{id}/check` | Check if session exists |
| `POST` | `/api/session/new` | Create empty session |
| `GET` | `/health` | Health check with model info + readiness status |

---

## Deployment

### Backend → Railway

1. Connect GitHub repo to Railway
2. Railway auto-detects the root `Dockerfile` (configured in `railway.toml`)
3. Set environment variables in Railway dashboard:

```
FIREWORKS_API_KEY=fw_your_key_here
FIREWORKS_ENDPOINT=https://api.fireworks.ai/inference/v1
FIREWORKS_MODEL_QUALITY=accounts/fireworks/models/deepseek-v4-flash
FIREWORKS_MODEL_FAST=accounts/fireworks/models/gpt-oss-120b
ALLOWED_ORIGINS=https://amd-hackthon-ll14.vercel.app,http://localhost:5173
PORT=8000
```

4. Health check configured at `/health` with 60s timeout
5. Auto-deploys on push to `main`

### Frontend → Vercel

1. Connect GitHub repo to Vercel
2. Set **Root Directory** to `frontend`
3. Set environment variable: `VITE_API_URL` = `https://amdhackthon-production.up.railway.app`
4. Auto-deploys on push to `main`

> **Note:** `VITE_*` vars are baked at build time. Always **Redeploy** after changing them.

---

## Key Technical Decisions

### Why AMD MI300X?
`gpt-oss-120b` on Fireworks AI runs on AMD Instinct MI300X at **646 tokens/sec** — enabling the fast-tier structured extraction calls (comparison matrix, conflict detection) to complete in 2–4 seconds each. This makes the 5-parallel-call architecture viable within a 90-second budget.

### Why Tiered Models?
Running 5 simultaneous calls on one large model caused rate-limit cascades (151s total). Splitting into `deepseek-v4-flash` (quality reasoning) + `gpt-oss-120b` (fast extraction) reduced end-to-end analysis to **~60 seconds**.

### Why `deepseek-v4-flash` over `-v4-pro`?
The `-pro` variant outputs `<think>` blocks before JSON, causing parse failures. `-flash` outputs clean JSON directly, is ~5x faster, and produces equivalent quality for document analysis.

### JSON Parsing Robustness
All LLM outputs pass through a 5-strategy fallback parser:
1. Direct `json.loads`
2. Brace extraction (handles prose preamble)
3. Trailing comma cleanup
4. Regex field extraction
5. LLM retry with explicit JSON-only instruction

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS 4, Framer Motion |
| UI Components | Radix UI, Lucide icons, shadcn/ui patterns |
| Backend | FastAPI, Python 3.11, uvicorn |
| AI Inference | Fireworks AI on AMD Instinct MI300X |
| LLM Models | deepseek-v4-flash (quality), gpt-oss-120b (fast) |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 |
| Vector DB | ChromaDB (in-memory) |
| PDF Parsing | PyMuPDF, pytesseract |
| PDF Export | reportlab |
| DOCX Export | python-docx |
| Rate Limiting | slowapi |
| Deployment | Railway (backend), Vercel (frontend) |

---

## Frontend Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Landing | Hero, feature showcase, Quick Scan entry point |
| `/dashboard` | Dashboard | Upload → Analyze → Results (Score, Risks, Matrix, Conflicts) |
| `/chat` | Chat | RAG copilot with ELI15 toggle + Snap & Check |
| `/demo` | Demo | Pre-loaded EcoTech Corp analysis (no API key needed) |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Analysis failed" immediately | Wrong model ID in Railway | Check `FIREWORKS_MODEL_QUALITY` — no spaces or `=` in value |
| "Connection error" on frontend | `VITE_API_URL` misconfigured | Must be exact URL, no trailing slash. Redeploy after change |
| 0 risks / empty matrix | `max_tokens` too low | Check Railway logs — model may be truncating |
| Analysis taking 140s+ | Using reasoning model | Switch to `deepseek-v4-flash` (not `-v4-pro`) |
| Vision returns "not configured" | `FIREWORKS_MODEL_VISION` unset | Set it to a vision-capable model in env |
| 429 rate limit errors | Too many concurrent requests | Reduce parallel calls or wait 60s |

---

## License

Built for the YFS Build for Good Hackathon 2025.
