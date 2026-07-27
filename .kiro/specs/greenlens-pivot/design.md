# Design Document — GreenLens Pivot

## Overview

This document describes the technical design for GreenLens, an AI-powered greenwashing/sustainability-claims detection platform. GreenLens began as "Clausify," an enterprise procurement-analysis tool, and has been fully rebranded and repositioned. This design is deliberately structured as a **content and presentation layer change on top of a preserved architecture skeleton**: the upload → embed → retrieve → 5-parallel-LLM-call → structured-response pipeline is untouched at the code-structure level. What changes is prompt content (domain), two new endpoints (Quick Scan, Snap & Check), one new response field (`greenwashScore`), and the full visual/copy layer.

### Goals

- Rewrite all 6 prompt files for the greenwashing domain while preserving every existing JSON output contract
- Add `greenwashScore` as an additive, backward-compatible field
- Add two new endpoints (`/api/quick-scan`, `/api/chat/vision`) following existing router/error-handling conventions
- Apply the GreenLens design system (green palette, renamed severity labels) on top of the existing component architecture
- Replace demo documents and pre-seeded chat content
- Preserve 100% of existing API function signatures, TypeScript types (additive only), and state management patterns

### Non-Goals

- No changes to `SessionManager`, `VectorStore`, `EmbeddingService`, `DocumentParser`, `PDFGenerator`, or `DOCXGenerator` — these are domain-agnostic and untouched
- No changes to the 5-parallel-`asyncio.gather` orchestration structure in `analysis_service.py` — only the prompt strings passed through it change
- No native mobile app (APK) — PWA-style camera access via HTML5 `capture` attribute only
- No plant/tree/biodiversity identification feature — vision use is scoped strictly to reading text/claims on product labels and packaging
- No changes to rate limiting infrastructure (`slowapi`) beyond adding new routes to existing limiter patterns
- Full WCAG validation is out of scope (requires manual testing per project convention); basic semantic HTML and keyboard operability for new components is in scope

---

## Architecture

```
backend/
├── models/
│   └── response.py              ← ADD: greenwashScore field, simplify field
├── prompts/
│   ├── system_prompt.py         ← REWRITE: sustainability analyst persona
│   ├── conflict_detection.py    ← REWRITE: claim vs data contradiction detection
│   ├── risk_analysis.py         ← REWRITE: greenwash flag detection
│   ├── executive_summary.py     ← REWRITE: verdict + greenwashScore
│   ├── recommendation.py        ← REWRITE: accountability action steps
│   ├── chat_copilot.py          ← REWRITE: sustainability chat persona + ELI15 branch
│   └── quick_scan.py            ← NEW: single-claim quick verdict prompt
├── routers/
│   ├── demo.py                  ← UPDATE: new demo document references
│   ├── chat.py                  ← UPDATE: add simplify flag passthrough, add vision sub-route
│   └── quick_scan.py            ← NEW: POST /api/quick-scan router
├── services/
│   ├── analysis_service.py      ← UPDATE: parse greenwashScore from summary call; comparison
│   │                                matrix prompt text updated inline
│   ├── llm_service.py           ← ADD: vision-capable completion method (reuses existing
│   │                                client/semaphore), MODEL_VISION config read
│   └── conflict_engine.py       ← UNCHANGED (only prompt text it calls changes)
└── sample_documents/
    ├── Demo_EcoTechCorp_SustainabilityReport.txt   ← NEW
    └── Demo_EcoTechCorp_PackagingClaims.txt         ← NEW

frontend/
├── src/
│   ├── lib/
│   │   ├── types.ts              ← ADD: greenwashScore?, simplify? (additive only)
│   │   └── api.ts                ← ADD: quickScan(), sendVisionMessage() functions
│   ├── styles/
│   │   └── theme.css             ← ADD/REPLACE: GreenLens token set (see steering doc)
│   └── app/
│       ├── components/
│       │   ├── NavigationBar.tsx       ← UPDATE: wordmark "GreenLens"
│       │   ├── Badges.tsx              ← UPDATE: label/color remap (additive props)
│       │   ├── GreenwashScoreGauge.tsx ← NEW component
│       │   ├── ClaimVsRealityRow.tsx   ← NEW component (wraps ComparisonRow data)
│       │   └── QuickScanPanel.tsx      ← NEW component
│       └── pages/
│           ├── Landing.tsx       ← UPDATE: copy + QuickScanPanel mount
│           ├── Dashboard.tsx     ← UPDATE: copy, GreenwashScoreGauge, ClaimVsRealityRow
│           ├── Chat.tsx          ← UPDATE: copy, ELI15 toggle, camera attach control
│           └── Demo.tsx          ← UPDATE: copy, new demo data rendering
```

### Data flow additions

```
Quick Scan flow (new, no session required):
  User types claim → App.quickScan(claim) → POST /api/quick-scan
    → LLMService.complete() [existing client/semaphore, fast model]
    → { verdict, whatToLookFor, confidence } → rendered inline, no navigation

Snap & Check flow (new, requires existing session):
  User attaches/captures image → App.sendVisionMessage(sessionId, image, question)
    → POST /api/chat/vision (multipart) → LLMService.completeVision()
    → [reuses existing httpx.AsyncClient + Semaphore(3)] → Vision_Model call
    → ChatResponse (same shape as /api/chat) → rendered in existing message-bubble UI

ELI15 flow (extends existing chat flow):
  User toggles ELI15 → App includes { simplify: true } in ChatRequest body
    → chat.py passes simplify flag → build_chat_prompt(..., simplify=True)
    → appends simplification instruction to existing prompt → same 4-section JSON output
```

No new state management library or pattern is introduced. `QuickScanPanel` uses local `useState` (no session/global state needed since it's stateless per-call). The vision chat flow reuses the existing Chat page's message-array state, adding an `imageUrl` field to the locally-rendered user message bubble only (not persisted to the backend `PersistedChatMessage` type, which remains text-only per Requirement 10.2).

---

## Components and Interfaces

### Backend

#### `models/response.py` additions

```python
class AnalysisResult(BaseModel):
    # ...existing fields unchanged...
    greenwashScore: int | None = None  # 0-100, None if not yet computed


class ChatRequest(BaseModel):
    sessionId: str
    question: str
    history: list[ChatHistoryMessage] = []
    simplify: bool = False  # NEW — ELI15 mode flag


class QuickScanRequest(BaseModel):
    claim: str  # max 500 chars, validated in router


class QuickScanResponse(BaseModel):
    verdict: str
    whatToLookFor: list[str]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
```

#### `prompts/quick_scan.py` (new)

```python
def build_quick_scan_prompt(claim: str) -> str:
    return f"""You are a sustainability claims analyst. A user has shown you a single
marketing/sustainability claim without any supporting document. Assess it on its own merits.

CLAIM: "{claim}"

Evaluate:
1. Is this claim independently verifiable, or is it inherently vague ("eco-friendly", "green", "natural")?
2. Does it reference a specific standard, certification, or measurable target?
3. Is this the kind of claim that regulators (e.g., ACCC, FTC Green Guides, EU Green Claims Directive) have flagged as commonly misleading?

Return ONLY valid JSON:
{{
  "verdict": "<1-2 sentence assessment of this claim's credibility on its own>",
  "whatToLookFor": ["<specific thing to verify>", "<specific thing to verify>", "<specific thing to verify>"],
  "confidence": "LOW|MEDIUM|HIGH"
}}"""
```

#### `services/llm_service.py` additions

```python
# New env-configured vision model, read alongside existing quality/fast models
self._model_vision = os.getenv("FIREWORKS_MODEL_VISION", "")

async def complete_vision(
    self,
    system_prompt: str,
    user_text: str,
    image_base64: str,
    image_mime: str,
    max_tokens: int = 800,
) -> str:
    """
    Vision-capable completion. Reuses self._client and self._semaphore.
    Raises LLMParseError if self._model_vision is not configured.
    """
    if not self._model_vision:
        raise LLMParseError("FIREWORKS_MODEL_VISION not configured")
    async with self._semaphore:
        payload = {
            "model": self._model_vision,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{image_mime};base64,{image_base64}"},
                        },
                    ],
                },
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        response = await self._client.post(
            f"{self._endpoint}/chat/completions", json=payload,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _sanitize_unicode(content)
```

This follows the exact same `httpx.AsyncClient` + `Semaphore(3)` + Fireworks OpenAI-compatible payload pattern as `_call_fireworks()`, just with a multi-part `content` array for the vision message — no new HTTP client, no new concurrency primitive.

#### `routers/quick_scan.py` (new)

Follows the existing router injection pattern (`_llm_service` module-level variable set in `main.py` startup, mirroring `upload.py`/`analyze.py`):

```python
router = APIRouter()
_llm_service = None  # injected in main.py startup

@router.post("/quick-scan", response_model=QuickScanResponse)
@limiter.limit("10/minute")
async def quick_scan(request: Request, body: QuickScanRequest):
    if not body.claim or len(body.claim) > 500:
        raise HTTPException(422, detail={"error": "...", "code": "INVALID_REQUEST"})
    prompt = build_quick_scan_prompt(body.claim)
    raw = await _llm_service.complete(get_system_prompt([]), prompt, max_tokens=400, fast=True)
    # parse via existing _strip_json_fences + json.loads, fallback on failure
    ...
```

#### `routers/chat.py` additions

- `POST /api/chat/vision` accepts `UploadFile` (image) + form fields (`sessionId`, `question` optional) — same multipart pattern as `routers/upload.py`.
- Existing `POST /api/chat` and `POST /api/chat/stream` handlers read the new `simplify: bool = False` field from `ChatRequest` and pass it to `build_chat_prompt(question, chunks, history, low_relevance, simplify=simplify)`.

#### `prompts/chat_copilot.py` — ELI15 branch

```python
def build_chat_prompt(question, chunks, history=None, low_relevance=False, simplify: bool = False) -> str:
    ...
    simplify_block = ""
    if simplify:
        simplify_block = """
SIMPLIFICATION MODE (ELI15): Explain as you would to a curious 15-year-old.
- Avoid jargon; if a technical term is unavoidable, define it in the same sentence
- Use short sentences and concrete comparisons
- Keep the same 4-section JSON structure — just simplify the language inside each field
"""
    return f"""...existing prompt body...{simplify_block}..."""
```

### Frontend

#### `types.ts` additions (additive only)

```typescript
export interface Analysis {
  // ...existing fields unchanged...
  greenwashScore?: number; // 0-100
}

// Quick Scan
export interface QuickScanResponse {
  verdict: string;
  whatToLookFor: string[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
}
```

#### `api.ts` additions

```typescript
export async function quickScan(claim: string): Promise<QuickScanResponse> {
  // same fetch + error-handling pattern as existing functions (e.g., analyzeDocuments)
}

export async function sendVisionMessage(
  sessionId: string,
  image: File,
  question?: string
): Promise<ChatResponse> {
  // multipart FormData POST to /api/chat/vision, same error-handling pattern as uploadDocuments
}
```

#### `GreenwashScoreGauge.tsx` (new)

```tsx
interface GreenwashScoreGaugeProps {
  score?: number; // undefined = loading/neutral state
}
```
- Renders numeral in Syne 800 (48-64px), band label in IBM Plex Sans 600 uppercase, thin arc/ring in band color
- Band logic: `score == null` → neutral grey ring + "—"; `0-30` → `--flag-red`; `31-60` → `--flag-amber`; `61-100` → `--leaf`

#### `ClaimVsRealityRow.tsx` (new)

```tsx
interface ClaimVsRealityRowProps {
  row: ComparisonRow; // existing type, unmodified — values keyed by "They Say" / "Data Shows" convention
}
```
- Renders `row.field` as the row label, then two side-by-side cells reading `row.values["They Say"]` (or first key) with `--paper` background and `row.values["Data Shows"]` (or second key) with `--parchment` background
- Backend prompts are instructed to key the `values` dict with exactly `"They Say"` and `"Data Shows"` so no additional parsing logic is needed on the frontend beyond existing `Record<string,string>` iteration

#### `QuickScanPanel.tsx` (new)

```tsx
interface QuickScanPanelProps {} // no props — self-contained, local state only
```
- Textarea + submit button, calls `quickScan()`, displays `verdict`, bulleted `whatToLookFor`, and a small confidence pill
- Mounted on `Landing.tsx` below or beside the existing upload zone; does not touch `useAppDispatch` or session state

#### `Badges.tsx` label/color remap

`RiskBadge` gains an internal label map (no prop interface change):
```tsx
const LABELS: Record<Risk['level'], string> = { HIGH: 'MISLEADING', MEDIUM: 'VAGUE', LOW: 'UNVERIFIED' };
const COLORS: Record<Risk['level'], string> = { HIGH: 'var(--flag-red)', MEDIUM: 'var(--flag-amber)', LOW: 'var(--flag-blue)' };
```
This is a pure internal-rendering change; `RiskBadge`'s existing `{ level: Risk['level'] }` prop signature is unchanged, so every call site (`Dashboard.tsx`, `Demo.tsx`) requires no edits.

#### Chat.tsx — ELI15 toggle + camera attach

- New local state: `const [simplify, setSimplify] = useState(false);` and `const [attachedImage, setAttachedImage] = useState<File | null>(null);`
- Toggle pill in header calls `setSimplify`; included in the request body for both `streamChatMessage` and any non-streaming send
- Camera icon button opens `<input type="file" accept="image/*" capture="environment" />`; on selection, sets `attachedImage` and renders a thumbnail chip; on send, if `attachedImage` is set, calls `sendVisionMessage()` instead of `streamChatMessage()`, then clears `attachedImage`

---

## Data Models

### Backend model diff summary

| Model | Change |
|---|---|
| `AnalysisResult` | + `greenwashScore: int \| None = None` |
| `ChatRequest` | + `simplify: bool = False` |
| `QuickScanRequest` (new) | `claim: str` |
| `QuickScanResponse` (new) | `verdict: str`, `whatToLookFor: list[str]`, `confidence: Literal["LOW","MEDIUM","HIGH"]` |

All other existing models (`Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `DocumentExcerpt`, `Evidence`, `StructuredAIResponse`, `UploadResponse`, `AnalyzeResponse`, `ChatResponse`, `ErrorResponse`) are **unchanged**.

### Frontend type diff summary

| Type | Change |
|---|---|
| `Analysis` | + `greenwashScore?: number` |
| `QuickScanResponse` (new) | `{ verdict: string; whatToLookFor: string[]; confidence: 'LOW'\|'MEDIUM'\|'HIGH' }` |

All other existing types are **unchanged**.

### Prompt output contract preservation table

| Prompt file | Old output shape | New output shape |
|---|---|---|
| `conflict_detection.py` | `{ conflicts: [{id, type, severity, documentA, documentB, explanation, recommendedAction}] }` | **identical shape**, content reframed to claim-vs-data |
| `risk_analysis.py` | `{ risks: [{id, level, description, sourceDocument, category}] }` | **identical shape**, content reframed to greenwash flags |
| `executive_summary.py` (merged w/ questions in `analysis_service.py`) | `{ executiveSummary, suggestedQuestions }` | `{ executiveSummary, suggestedQuestions, greenwashScore }` — **one field added** |
| `recommendation.py` | `{ title, summary, nextSteps, confidence }` | **identical shape**, content reframed to accountability steps |
| comparison matrix (inline prompt in `analysis_service.py`) | `{ comparisonMatrix: [{field, values, winner}] }` | **identical shape**, `values` keyed by `"They Say"`/`"Data Shows"` |
| `chat_copilot.py` | `{ answer, evidence, risks, recommendation }` | **identical shape**, persona reframed, optional simplify instruction appended |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

This feature mixes prompt/content rewrites (not testable via property-based testing — they require human judgment on prompt quality) with several genuinely parameterized behaviors: score clamping, severity-label mapping, and conditional endpoint availability. The following properties apply to the latter category.

---

### Property 1: Greenwash Score is always clamped to [0, 100]

*For any* raw numeric value returned by the LLM for `greenwashScore` (including out-of-range or negative values), the API SHALL store a clamped integer value where `0 <= greenwashScore <= 100`.

**Validates: Requirements 2.2**

---

### Property 2: Missing or non-numeric score falls back to 50

*For any* LLM response where `greenwashScore` is absent, `null`, a string, or otherwise non-numeric, the API SHALL set `greenwashScore = 50` and SHALL log a warning, rather than raising an exception or leaving the field in an invalid state.

**Validates: Requirements 2.3**

---

### Property 3: Risk level to Greenwash Flag label/color mapping is total and exclusive

*For any* `Risk.level` value in `{HIGH, MEDIUM, LOW}`, the `RiskBadge` component SHALL render exactly one of `{MISLEADING/--flag-red, VAGUE/--flag-amber, UNVERIFIED/--flag-blue}` respectively, and SHALL NOT render any other label or color combination for any input value.

**Validates: Requirements 4.1**

---

### Property 4: Quick Scan rejects invalid claims and never crashes

*For any* string input to `POST /api/quick-scan`, IF the string is empty or exceeds 500 characters, THEN the API SHALL return HTTP 422 with the `ErrorResponse` shape; OTHERWISE the API SHALL return HTTP 200 with the `QuickScanResponse` shape (using fallback values if LLM parsing fails), and SHALL NOT return an unhandled HTTP 500 for any string input within the length constraint.

**Validates: Requirements 6.1, 6.3**

---

### Property 5: Vision endpoint availability is determined solely by configuration

*For any* request to `POST /api/chat/vision`, IF `FIREWORKS_MODEL_VISION` is unset or empty, THEN the API SHALL return a graceful `ErrorResponse`/fallback `ChatResponse` indicating vision analysis is not configured, and SHALL NOT attempt an HTTP call to the Fireworks endpoint with an empty model string; IF it is set, THEN the API SHALL attempt the vision completion call.

**Validates: Requirements 7.5, 11.2**

---

### Property 6: ELI15 flag defaults to False and never breaks output shape

*For any* `ChatRequest` JSON body that omits the `simplify` field, the API SHALL treat `simplify` as `False` and SHALL produce a `StructuredAIResponse` with the same 4 required fields (`answer`, `evidence`, `risks`, `recommendation`) regardless of the `simplify` value.

**Validates: Requirements 8.3, 8.4**

---

## Error Handling

### New endpoint errors

- `/api/quick-scan`: validation errors (empty/too-long claim) → HTTP 422 with `ErrorResponse`; LLM/parse failures → fallback `QuickScanResponse` with `confidence: "LOW"` and a generic verdict message (never a 500), consistent with the existing analysis pipeline's graceful-partial-results philosophy.
- `/api/chat/vision`: file validation errors (size/MIME) → HTTP 422 with `ErrorResponse`, mirroring `routers/upload.py`; missing vision model config → fallback `ChatResponse` explaining the limitation (per Property 5); Fireworks API failures → same rate-limit-retry behavior as `LLMService.complete()` where applicable, otherwise fallback response.

### Existing error handling (preserved)

All existing error handling — the global exception handler in `main.py`, the `ErrorResponse` envelope, `slowapi` rate limiting, and the 5-strategy JSON parsing pipeline — is reused without modification for both new and rewritten-prompt endpoints.

### Backward compatibility

Because `greenwashScore` and `simplify` are both optional/defaulted fields, any client (old or new) sending requests without these fields continues to function. Any client reading responses without expecting `greenwashScore` simply ignores the extra field (TypeScript optional field, Python `| None` default).

---

## Testing Strategy

### PBT applicability assessment

Most of this feature is prompt-content rewriting, which is not amenable to property-based testing — prompt quality requires human/LLM-output evaluation, not generative input testing. However, six genuinely parameterized behaviors are identified above (score clamping, fallback, label mapping, input validation, config-gated availability, and default-flag safety) and are appropriate for property-based tests.

**Chosen PBT library**: `fast-check` (frontend, already used per the `greenlens-ui-redesign` spec) and `hypothesis` (backend, Python-native equivalent) for the backend-side properties (1, 2, 4, 5, 6).

### Unit tests (example-based)

- `analysis_service.py`: summary-and-questions parsing includes `greenwashScore` extraction with clamping and fallback
- `routers/quick_scan.py`: valid claim returns 200, empty claim returns 422, 501-char claim returns 422
- `routers/chat.py`: vision route returns configured-fallback response when `FIREWORKS_MODEL_VISION` is empty
- `Badges.tsx` (`RiskBadge`): each of the 3 `Risk.level` values renders the correct label text and CSS variable reference
- `GreenwashScoreGauge.tsx`: renders neutral state for `undefined`, correct band color for representative scores in each of the 3 bands and at both boundaries (30/31, 60/61)
- `ClaimVsRealityRow.tsx`: renders both claim and reality cells with correct background tokens

### Property-based tests

Tag format: `Feature: greenlens-pivot, Property {N}: {property_text}`

1. Score clamping (Property 1) — `hypothesis.strategies.integers()` including out-of-range and negative values, backend
2. Score fallback (Property 2) — `hypothesis.strategies.one_of(none(), text(), floats())`, backend
3. Risk label/color mapping (Property 3) — `fc.constantFrom('HIGH', 'MEDIUM', 'LOW')`, frontend
4. Quick Scan input validation (Property 4) — `hypothesis.strategies.text()` with length variation including boundary at 500/501 chars, backend
5. Vision config gating (Property 5) — `hypothesis.strategies.one_of(none(), just(''), text(min_size=1))` for the env var value, backend
6. ELI15 default safety (Property 6) — `hypothesis.strategies.booleans()` plus omission case, backend

### Integration / smoke tests

- Existing backend test suite in `backend/tests/` (`test_analysis.py`, `test_chat.py`, `test_conflict.py`, `test_upload.py`, `test_session.py`, `test_embedding.py`, `test_error_format.py`) continues to pass unmodified, confirming the pivot did not break existing contracts
- New smoke test confirms `GET /api/demo` returns an `AnalysisResult` with `conflicts.length >= 1`, `risks.length >= 3`, and `greenwashScore` in `[0, 30]` per Requirement 9.2–9.3
- Grep-based smoke test: no remaining "Clausify" brand string in user-facing `.tsx` copy (excluding the `Feature: clausify-ui-redesign` test-tag comments in `__tests__` files, which intentionally retain the original spec name for traceability to the historical base-redesign spec) — this has already been verified clean as of the full codebase rebrand pass

### Testing configuration

- Backend: `pytest` (existing `pytest.ini`) + `hypothesis` added to `requirements.txt`
- Frontend: `Vitest` + `@testing-library/react` + `fast-check` (already referenced in the `greenlens-ui-redesign` spec's testing strategy)
- Property tests configured for 100+ iterations each
