# 🛠️ SETUP GUIDE — GreenLens

## Para sa mga Teammates (TL;DR)

### Kailangan mo:
- Node.js 20+ → https://nodejs.org
- Python 3.11+ → https://www.python.org/downloads/
- Git → https://git-scm.com

### Step 1: Clone

```bash
git clone https://github.com/your-username/AmdHackthon-main.git
cd AmdHackthon-main
```

### Step 2: Backend

```bash
cd backend
cp .env.example .env
```

**EDIT `backend/.env`** — ilagay yung Fireworks API key:
```
FIREWORKS_API_KEY=fw_xxxxxxxxxxxxxxxxxxxxxxxx
```
(Kuhanin ang key kay Rhen o sa group chat)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

✅ Check: Open http://localhost:8000/health — dapat may JSON response

### Step 3: Frontend (bagong terminal)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

✅ Check: Open http://localhost:5173 — dapat may landing page

### Step 4: Verify

- Go to http://localhost:5173/demo — may pre-loaded analysis
- Upload a PDF sa landing page — should analyze in ~60s
- Go to /chat after analysis — type a question

---

## Kung May Error

### "FIREWORKS_API_KEY is required"
→ Hindi mo na-set yung .env file. Copy `.env.example` to `.env` at lagyan ng key.

### "Module not found" (Python)
→ `pip install -r requirements.txt` ulit. Make sure naka-activate yung venv.

### "npm ERR!" or "Module not found" (Frontend)
→ `npm install` ulit sa `frontend/` folder.

### Frontend can't connect to backend
→ Make sure backend is running on port 8000. Check `frontend/.env` has `VITE_API_URL=http://localhost:8000`

### "chromadb" or "sentence-transformers" download error
→ First run downloads the embedding model (~90MB). Wait for it to finish.

---

## Git Workflow

```bash
# Always start from dev-1
git checkout dev-1
git pull origin dev-1

# Make your branch
git checkout -b feature/my-changes

# ... gawa ka ng changes ...

git add .
git commit -m "feat: what I did"
git push -u origin feature/my-changes

# → Create Pull Request to dev-1 sa GitHub
```

**HUWAG direct push sa `main` or `dev-1`!** Always PR.

---

## Kung Gagamit ka ng AI Agent (Kiro/Cursor/Copilot)

Point the AI to read this file first:
- `README.md` — full system overview
- `frontend/src/lib/types.ts` — TypeScript interfaces (source of truth)
- `backend/models/response.py` — backend data schemas
- `backend/main.py` — how services are wired together

The AI can then understand the whole system and help you code.
