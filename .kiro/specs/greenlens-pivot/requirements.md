# Requirements Document

## Introduction

This document specifies requirements for pivoting the Clausify AI platform into **GreenLens** — an AI-powered greenwashing detection tool for the YFS Build for Good Hackathon (AI for Sustainability track). The pivot repurposes ~85% of the existing FastAPI + React + Fireworks AI (AMD MI300X) codebase: the document upload, RAG, and 5-parallel-LLM-call analysis architecture remain unchanged. What changes is the *domain* — from procurement document conflict detection to corporate sustainability claim verification — along with the visual brand, prompt content, and three new user-facing capabilities (Greenwash Score, Quick Scan, Snap & Check vision chat). All existing API contracts, TypeScript types, and state management patterns are preserved wherever possible; additive fields are used instead of breaking changes.

## Glossary

- **App**: The GreenLens frontend (formerly Clausify) React + TypeScript + Tailwind application.
- **API**: The GreenLens FastAPI backend (formerly Clausify backend).
- **Analysis_Pipeline**: The 5-parallel-`asyncio.gather` LLM orchestration in `analysis_service.py`.
- **Greenwash_Score**: A 0–100 integer credibility rating generated per analysis, banded into "Mostly Greenwashing" (0–30), "Vague / Mixed Signals" (31–60), and "Credible" (61–100).
- **Greenwash_Flag**: A `Risk` object (existing `HIGH`/`MEDIUM`/`LOW` enum, unchanged at the data layer) whose display label is remapped to `MISLEADING` (HIGH), `VAGUE` (MEDIUM), or `UNVERIFIED` (LOW).
- **Contradiction**: A `Conflict` object (existing type, unchanged at the data layer) representing a detected mismatch between a marketing claim and underlying report data, rendered via `ContradictionAlert`.
- **Claim_vs_Reality_Row**: A `ComparisonRow` object (existing type, unchanged at the data layer) representing one claim compared against the corresponding data point, rendered via `ClaimVsRealityRow`.
- **Quick_Scan**: A new lightweight analysis mode that accepts a single typed claim (no document upload) and returns a short verdict.
- **Snap_And_Check**: A new chat capability where the user attaches or captures a photo of a product label/packaging/marketing material, and the assistant analyzes the visible claims using a vision-capable model call.
- **ELI15_Mode**: A chat response-complexity toggle that instructs the LLM to simplify its language for a 14–18 year old audience.
- **Vision_Model**: A Fireworks AI vision-capable chat completion model (e.g., an `*-vision-instruct` class model) used exclusively for Snap_And_Check image analysis.
- **Demo_Documents**: The pre-loaded sample documents used by the `/api/demo` endpoint and Demo page, replacing the existing procurement sample documents with a fictional "EcoTech Corp" sustainability report and contradicting packaging claim set.
- **Design_System**: The GreenLens token set (colors, typography, shape) specified in the `greenlens-design-system` steering document, layered on top of the existing Clausify token architecture.
- **Session**: The existing `SessionManager`-backed upload/analysis session, unchanged structurally.

---

## Requirements

### Requirement 1: Backend Domain Rebrand — Prompts

**User Story:** As a hackathon judge evaluating the product, I want the AI's analysis to be clearly and consistently about sustainability claim verification rather than procurement documents, so that the product's stated purpose matches its actual behavior.

#### Acceptance Criteria

1. THE API SHALL replace the system persona in `prompts/system_prompt.py` with a sustainability-claims-analyst persona while preserving the existing 5-step cognitive process structure (UNDERSTAND → EXTRACT → ANALYZE → SYNTHESIZE → ADVISE).
2. THE API SHALL replace `prompts/conflict_detection.py` with logic that identifies contradictions between marketing/packaging claims and underlying sustainability report data, using the same JSON output shape as the existing `Conflict` model (`id`, `type`, `severity`, `documentA`, `documentB`, `explanation`, `recommendedAction`).
3. THE API SHALL replace `prompts/risk_analysis.py` with logic that identifies Greenwash_Flags (misleading claims, vague claims, unverified claims) using the same JSON output shape as the existing `Risk` model (`id`, `level`, `description`, `sourceDocument`, `category`).
4. THE API SHALL replace `prompts/executive_summary.py` with logic that produces a sustainability verdict summary and SHALL additionally instruct the model to output an integer `greenwashScore` field between 0 and 100.
5. THE API SHALL replace `prompts/recommendation.py` with logic that produces accountability action steps (e.g., specific questions to ask the company) using the same JSON output shape as the existing `Recommendation` model (`title`, `summary`, `nextSteps`, `confidence`).
6. THE API SHALL replace the comparison matrix prompt in `analysis_service.py` with logic that produces Claim_vs_Reality_Rows comparing "What They Claim" against "What The Data Shows" for each identified claim, using the same JSON output shape as the existing `ComparisonRow` model (`field`, `values`, `winner`).
7. THE API SHALL replace `prompts/chat_copilot.py` with a sustainability-analyst persona while preserving the existing language-matching behavior (responding in the user's input language) and the existing 4-section output structure (`answer`, `evidence`, `risks`, `recommendation`).
8. WHEN any rewritten prompt is sent to the LLM, THE API SHALL preserve the existing JSON-only output instruction pattern and the existing 5-strategy JSON parsing pipeline in `analysis_service.py` and `llm_service.py` without modification to the parsing logic itself.

---

### Requirement 2: Greenwash Score Field

**User Story:** As a user, I want a single clear number representing how credible a company's sustainability claims are, so that I can quickly assess and share the result.

#### Acceptance Criteria

1. THE API SHALL add an optional integer field `greenwashScore` (0–100) to the `AnalysisResult` model in `models/response.py`, defaulting to `None` when not computed.
2. WHEN the executive-summary-and-questions LLM call succeeds, THE API SHALL parse a `greenwashScore` integer from the response and clamp it to the range 0–100 inclusive.
3. IF the LLM response omits `greenwashScore` or returns a non-numeric value, THEN THE API SHALL fall back to computing a default score of 50 and SHALL log a warning.
4. THE App SHALL add an optional field `greenwashScore?: number` to the `Analysis` interface in `frontend/src/lib/types.ts`.
5. THE App SHALL render a `GreenwashScoreGauge` component on the Dashboard and Demo pages showing the numeral, band label ("Mostly Greenwashing" / "Vague / Mixed Signals" / "Credible"), and a color per the band (`--flag-red` for 0–30, `--flag-amber` for 31–60, `--leaf` for 61–100).
6. WHEN `greenwashScore` is `undefined` or `null` in the `Analysis` object, THE App SHALL render the `GreenwashScoreGauge` in a neutral/loading state rather than omitting it or throwing an error.

---

### Requirement 3: Visual Rebrand — Design Tokens and Typography

**User Story:** As a user, I want the interface to visually communicate sustainability and credibility rather than enterprise procurement, so that the product's identity is coherent and memorable.

#### Acceptance Criteria

1. THE App SHALL define the GreenLens token set in `theme.css` per the `greenlens-design-system` steering document: `--ink: #0A120E`, `--lead: #131F19`, `--graphite: #1C2B23`, `--rule: #24352C`, `--ash: #9BAFA3`, `--ghost: #4E6157`, `--leaf: #3DDC84`, `--leaf-dim: rgba(61,220,132,0.08)`, `--leaf-border: rgba(61,220,132,0.22)`, `--paper: #F3F0E6`, `--parchment: #E9E4D6`, `--flag-red: #F04452`, `--flag-amber: #F0A937`, `--flag-blue: #5FA8D3`, and their `-dim` tint variants.
2. THE App SHALL preserve `--amd-signal: #ED1C24` unchanged and SHALL use it exclusively for the `AMDBadge` component, never for `--flag-red` or any Greenwash_Flag rendering.
3. THE App SHALL continue to use Syne (700/800) for display text, IBM Plex Sans (400/500/600) for body/UI text, and IBM Plex Mono (400/500/600) for evidence/data values, matching the existing Clausify typography system.
4. WHEN any component previously referenced `--volt`, `--volt-dim`, or `--volt-border` (from the Clausify UI redesign), THE App SHALL reference `--leaf`, `--leaf-dim`, or `--leaf-border` respectively after the GreenLens rebrand.
5. THE App SHALL rename the brand wordmark from "Clausify" + "AI" to "GreenLens" in the `NavigationBar` logo mark, with "Green" in Syne 700 default text color and "Lens" in Syne 700 colored `--leaf`.

---

### Requirement 4: Greenwash Flag and Contradiction Display

**User Story:** As a user reviewing analysis results, I want severity-colored flags and contradiction alerts that clearly communicate greenwashing risk, so that I can immediately identify the most concerning claims.

#### Acceptance Criteria

1. THE App SHALL rename and recolor the existing `RiskBadge` component's rendered labels: `HIGH` → "MISLEADING" (`--flag-red` background/text), `MEDIUM` → "VAGUE" (`--flag-amber`), `LOW` → "UNVERIFIED" (`--flag-blue`), while preserving the underlying `Risk.level` enum values (`HIGH`/`MEDIUM`/`LOW`) unchanged in the data layer.
2. THE App SHALL rename the existing `ConflictAlert` component's rendered header text from "CONFLICTS DETECTED" to "CONTRADICTION DETECTED" and SHALL change its left-border and label color from `--amd-signal` to `--flag-red`.
3. WHEN `analysis.conflicts` contains one or more items, THE App SHALL render the `ContradictionAlert` banner; WHEN it is empty, THE App SHALL NOT render the banner — preserving the existing conditional-render behavior from the Clausify `ConflictAlert`.
4. THE App SHALL rename the Dashboard's "Comparison Matrix" card title to "Claim vs. Reality" and SHALL render each `ComparisonRow` as a `ClaimVsRealityRow` with two labeled columns ("They Say" using `--paper` background, "Data Shows" using `--parchment` background) instead of a generic multi-vendor table.

---

### Requirement 5: Landing, Dashboard, Chat, Demo Copy Rebrand

**User Story:** As a prospective user, I want all page copy to describe greenwashing detection rather than procurement analysis, so that the product's purpose is immediately clear.

#### Acceptance Criteria

1. THE Landing_Page SHALL replace the existing headline, subheadline, and stats-row copy with sustainability-claim-verification framing (e.g., referencing uploading sustainability reports/marketing claims and detecting greenwashing) while preserving the existing upload zone drag-and-drop logic, file validation logic, and analyze-button flow unchanged.
2. THE Landing_Page SHALL preserve the AMD MI300X hackathon badge and performance stats row structure, updating only text copy, not the underlying benchmark-fetching logic (`getBenchmarkSpeedup`).
3. THE Dashboard_Page SHALL replace card titles and section labels per Requirement 4.4 and SHALL add the `GreenwashScoreGauge` above the existing `AnalysisCardGrid`, without altering the sidebar's document-list rendering logic or session/export button wiring.
4. THE Chat_Page SHALL update the AI persona introduction copy and quick-question chip suggestions to sustainability-claim topics (e.g., "Is this claim backed by data?", "What's Scope 3 and why does it matter?") while preserving the existing SSE streaming logic, message history state, and evidence-section rendering structure.
5. THE Demo_Page SHALL populate from new Demo_Documents (an "EcoTech Corp" sustainability report and contradicting packaging/marketing claim set) returned by `GET /api/demo`, replacing the existing procurement demo dataset, without altering the `getDemoData()` call signature or `DemoResponse` type shape.

---

### Requirement 6: Quick Scan (Text-Only Entry Point)

**User Story:** As a user without a document to upload, I want to type a single sustainability claim and get an instant credibility verdict, so that I can quickly fact-check something I saw without any upload friction.

#### Acceptance Criteria

1. THE API SHALL expose a new endpoint `POST /api/quick-scan` accepting a JSON body `{ claim: string }` where `claim` is a non-empty string of at most 500 characters.
2. WHEN `POST /api/quick-scan` receives a valid request, THE API SHALL send the claim to the LLM with a dedicated quick-scan prompt and SHALL return a JSON response `{ verdict: string, whatToLookFor: string[], confidence: "LOW" | "MEDIUM" | "HIGH" }` within a single LLM call (no document retrieval required).
3. IF the `claim` field is empty or exceeds 500 characters, THEN THE API SHALL return HTTP 422 with the existing `ErrorResponse` envelope shape (`error`, `code`, `details`).
4. THE API SHALL apply the existing `slowapi` rate-limiting pattern to `/api/quick-scan` at a rate no more permissive than the existing `/api/chat` limit (10/min).
5. THE App SHALL add a "Quick Scan" entry point on the Landing_Page, presented alongside the existing document upload zone, that accepts free-text input and displays the returned verdict, look-for list, and confidence level without requiring a session or navigation to the Dashboard.
6. THE App SHALL add a corresponding `quickScan(claim: string)` function to `frontend/src/lib/api.ts` following the existing fetch/error-handling pattern used by other API functions in that file.

---

### Requirement 7: Snap & Check (Vision-Enabled Chat)

**User Story:** As a user standing in a store, I want to photograph a product label or packaging claim and ask the AI whether it's legitimate, so that I can fact-check claims in the moment without needing a pre-uploaded document.

#### Acceptance Criteria

1. THE API SHALL expose a new endpoint `POST /api/chat/vision` accepting a multipart request containing an image file and an optional text question, associated with an existing `sessionId`.
2. WHEN `POST /api/chat/vision` receives a valid image, THE API SHALL send the image and question to a Vision_Model via the Fireworks AI chat completions endpoint using an image-capable payload (base64-encoded image content per the OpenAI-compatible vision message format), reusing the existing `LLMService` HTTP client and semaphore concurrency control.
3. THE API SHALL return a `ChatResponse` with the same shape as the existing `/api/chat` endpoint (`messageId`, `role`, `structuredResponse`, `processingTimeMs`), where `structuredResponse.answer` describes the claims visible in the image and any greenwashing concerns identified.
4. IF the uploaded image exceeds 10MB or is not a supported image MIME type (`image/png`, `image/jpeg`, `image/jpg`, `image/webp`), THEN THE API SHALL return HTTP 422 with the existing `ErrorResponse` envelope shape, matching the existing upload validation pattern in `routers/upload.py`.
5. IF the configured Vision_Model is unavailable or the Fireworks API call fails, THEN THE API SHALL return a `ChatResponse` with a graceful fallback `structuredResponse.answer` explaining that image analysis is temporarily unavailable, rather than a 500 error.
6. THE App SHALL add a camera/attach control to the Chat_Page input bar that opens the device camera on mobile (via `<input type="file" accept="image/*" capture="environment">`) or a file picker on desktop, and SHALL render the selected image as a thumbnail chip above the input bar before sending.
7. WHEN an image is attached and the user sends a message, THE App SHALL call the vision endpoint instead of the standard streaming chat endpoint and SHALL render the response using the same AI-message-bubble structure (ANSWER/EVIDENCE/RISK/RECOMMENDATION sections) as standard chat responses.

---

### Requirement 8: ELI15 Mode

**User Story:** As a 14-to-18-year-old user, I want the option to see simplified AI explanations, so that technical sustainability jargon doesn't block my understanding.

#### Acceptance Criteria

1. THE App SHALL add an ELI15_Mode toggle control to the Chat_Page header, defaulting to the "Expert" (off) state.
2. WHEN ELI15_Mode is active, THE App SHALL include an additional flag in the chat request body (e.g., `simplify: true`) sent to `POST /api/chat` and `POST /api/chat/stream`.
3. WHEN the API receives a chat request with `simplify: true`, THE API SHALL append an explicit simplification instruction to the chat prompt (e.g., instructing the model to explain concepts as it would to a 15-year-old, avoiding jargon or defining it immediately when used) without altering the existing 4-section JSON output structure.
4. THE ChatRequest model in `models/response.py` SHALL add an optional field `simplify: bool = False` that defaults to `False` when omitted, preserving backward compatibility with existing chat requests that do not include this field.

---

### Requirement 9: Demo Documents Replacement

**User Story:** As a hackathon judge trying the Demo page, I want to see a realistic greenwashing example without uploading anything, so that I can immediately understand the product's value.

#### Acceptance Criteria

1. THE API SHALL replace the sample documents referenced by `routers/demo.py` with a fictional "EcoTech Corp" sustainability report (containing at least one carbon-neutrality claim with unaccounted Scope 2/3 emissions) and a contradicting product packaging/marketing claim set (containing at least one "100% recycled" or equivalent claim not supported by the report).
2. WHEN `GET /api/demo` is called, THE API SHALL return a `DemoResponse` whose `analysis.conflicts` contains at least one Contradiction between the two Demo_Documents and whose `analysis.risks` contains at least three Greenwash_Flags, without changing the `DemoResponse` type shape.
3. THE API SHALL ensure the Demo_Documents analysis includes a computed `greenwashScore` in the 0–30 band ("Mostly Greenwashing") to demonstrate the scoring feature clearly in the pre-loaded demo.
4. THE App SHALL update the Demo_Page's pre-seeded chat messages to reflect sustainability-claim questions and answers consistent with the new Demo_Documents content.

---

### Requirement 10: API and Type Preservation

**User Story:** As a developer, I want all existing, non-domain-specific API contracts and TypeScript types to remain functional after the pivot, so that the rebrand does not introduce regressions.

#### Acceptance Criteria

1. THE App SHALL preserve the exact function signatures of `uploadDocuments()`, `analyzeDocuments()`, `streamChatMessage()`, `exportReport()`, `getDemoData()`, and `getSuggestedQuestions()` in `frontend/src/lib/api.ts`.
2. THE App SHALL preserve all existing fields on `UploadedDocument`, `UploadResponse`, `Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `Analysis`, `AnalyzeResponse`, `Evidence`, `StructuredAIResponse`, `ChatResponse`, `PreSeededMessage`, and `DemoResponse` in `frontend/src/lib/types.ts`, adding only the new optional `greenwashScore` field to `Analysis`.
3. THE API SHALL preserve all existing fields on `Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `AnalysisResult`, `UploadResponse`, `AnalyzeResponse`, `ChatResponse`, and `ErrorResponse` Pydantic models in `models/response.py`, adding only the new optional `greenwashScore` field to `AnalysisResult` and the new optional `simplify` field to `ChatRequest`.
4. THE API SHALL preserve the existing 5-parallel-call architecture, semaphore concurrency control, per-call timeout wrapping, and graceful-partial-results fallback behavior in `analysis_service.py` without structural modification — only prompt content changes.
5. IF any new endpoint (`/api/quick-scan`, `/api/chat/vision`) fails, THEN THE API SHALL return errors using the existing `ErrorResponse` envelope shape (`error`, `code`, `details`) consistent with all other endpoints.

---

### Requirement 11: Configuration for Vision Model

**User Story:** As a developer deploying GreenLens, I want the vision model to be configurable via environment variables, so that the vision feature can be enabled, disabled, or swapped without code changes.

#### Acceptance Criteria

1. THE API SHALL read a new environment variable `FIREWORKS_MODEL_VISION` for the vision-capable model identifier, with a documented default value in `.env.example`.
2. IF `FIREWORKS_MODEL_VISION` is not set, THEN THE API SHALL disable the `/api/chat/vision` endpoint's model call path and SHALL return a clear "vision analysis not configured" message in the `ErrorResponse` shape rather than attempting a call with an empty model string.
3. THE API SHALL document `FIREWORKS_MODEL_VISION` in `README.md`'s environment variable table, consistent with the existing documentation pattern for `FIREWORKS_MODEL_QUALITY` and `FIREWORKS_MODEL_FAST`.
