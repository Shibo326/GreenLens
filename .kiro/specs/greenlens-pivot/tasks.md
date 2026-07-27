# Implementation Plan: GreenLens Pivot

## Overview

This plan implements the pivot of Clausify AI into GreenLens for the YFS Build for Good Hackathon. Implementation proceeds in dependency order: backend models/config → backend prompts → backend new endpoints → frontend types/api → frontend design tokens → frontend components → frontend pages → demo content → verification. Reference `.kiro/steering/greenlens-master-plan.md` and `.kiro/steering/greenlens-design-system.md` throughout.

**DO NOT BREAK:** existing function signatures in `frontend/src/lib/api.ts`, existing fields in `frontend/src/lib/types.ts` and `backend/models/response.py` (additive changes only), the 5-parallel-call structure in `analysis_service.py`, and the existing backend test suite in `backend/tests/`.

## Tasks

- [ ] 1. Backend foundation: models, config, quick-scan prompt
  - [ ] 1.1 Add additive fields to response models
    - Add `greenwashScore: int | None = None` to `AnalysisResult` in `backend/models/response.py`
    - Add `simplify: bool = False` to `ChatRequest` in `backend/models/response.py`
    - Add new `QuickScanRequest` model (`claim: str`) and `QuickScanResponse` model (`verdict: str`, `whatToLookFor: list[str]`, `confidence: Literal["LOW","MEDIUM","HIGH"]`) to `backend/models/response.py`
    - _Requirements: 2.1, 6.1, 6.2, 8.4, 10.3_

  - [ ] 1.2 Add vision model configuration
    - Add `FIREWORKS_MODEL_VISION` env var read in `LLMService.__init__` (`backend/services/llm_service.py`), defaulting to empty string
    - Document `FIREWORKS_MODEL_VISION` in `backend/.env.example` with a suggested vision-capable model identifier and a comment explaining it's optional
    - Document `FIREWORKS_MODEL_VISION` in `README.md`'s environment variable table
    - _Requirements: 11.1, 11.3_

  - [ ] 1.3 Create quick-scan prompt module
    - Create `backend/prompts/quick_scan.py` with `build_quick_scan_prompt(claim: str) -> str`, per the design document's prompt template
    - _Requirements: 6.2_

- [ ] 2. Backend: rewrite the 5 core analysis prompts for the greenwashing domain
  - [ ] 2.1 Rewrite system_prompt.py
    - Replace the procurement/M&A analyst persona in `build system prompt` with a sustainability-claims-analyst persona
    - Preserve the existing 5-step cognitive process structure (UNDERSTAND → EXTRACT → ANALYZE → SYNTHESIZE → ADVISE) and the `doc_list` parameter signature
    - _Requirements: 1.1_

  - [ ] 2.2 Rewrite conflict_detection.py
    - Reframe `build_conflict_prompt` to detect contradictions between marketing/packaging claims (Document A) and sustainability report data (Document B)
    - Preserve the exact function signature `build_conflict_prompt(doc_a_chunks, doc_b_chunks, doc_a_name, doc_b_name)` and the exact output JSON shape (`conflicts: [{id, type, severity, documentA, documentB, explanation, recommendedAction}]`)
    - _Requirements: 1.2, 10.4_

  - [ ] 2.3 Rewrite risk_analysis.py
    - Reframe `build_risk_prompt` to identify Greenwash Flags: misleading claims (HIGH), vague/unmeasurable claims (MEDIUM), unverified/uncertified claims (LOW)
    - Preserve the exact function signature and output JSON shape (`risks: [{id, level, description, sourceDocument, category}]`), and preserve the existing `_format_chunks_for_risk` chunk-selection logic unchanged
    - _Requirements: 1.3, 10.4_

  - [ ] 2.4 Rewrite executive_summary.py and add greenwashScore parsing
    - Reframe `build_summary_prompt` (or the merged summary+questions prompt in `analysis_service.py`) to produce a sustainability verdict
    - Add `greenwashScore` (integer 0-100) to the requested JSON output alongside `executiveSummary` and `suggestedQuestions`
    - In `analysis_service.py`'s `_generate_summary_and_questions`, parse `greenwashScore` from the response, clamp to [0,100], and fall back to 50 with a logged warning if missing/non-numeric (Property 1, Property 2)
    - Update the return type/unpacking of `_generate_summary_and_questions` to include the score, and thread it into the `AnalysisResult` construction in `run_full_analysis`
    - _Requirements: 1.4, 2.2, 2.3_

  - [ ] 2.5 Rewrite recommendation.py
    - Reframe `build_recommendation_prompt` to produce accountability action steps (specific questions to ask the company, verification steps)
    - Preserve the exact function signature and output JSON shape (`title`, `summary`, `nextSteps`, `confidence`)
    - _Requirements: 1.5_

  - [ ] 2.6 Update comparison matrix prompt in analysis_service.py
    - Reframe `COMPARISON_MATRIX_PROMPT` to produce Claim vs. Reality rows, instructing the model to key each row's `values` dict with `"They Say"` and `"Data Shows"`
    - Preserve the exact output JSON shape (`comparisonMatrix: [{field, values, winner}]`)
    - _Requirements: 1.6_

  - [ ] 2.7 Rewrite chat_copilot.py and add ELI15 branch
    - Reframe `build_chat_prompt`'s persona and reasoning framework for sustainability claims analysis
    - Preserve the existing language-matching instruction block and the existing 4-section output JSON shape (`answer`, `evidence`, `risks`, `recommendation`)
    - Add a new `simplify: bool = False` parameter to `build_chat_prompt`; when `True`, append the ELI15 simplification instruction block from the design document
    - _Requirements: 1.7, 8.3_

  - [ ] 2.8 Wire simplify flag through chat router
    - In `routers/chat.py`, read `simplify` from the incoming `ChatRequest` body (both `/api/chat` and `/api/chat/stream` handlers) and pass it to `build_chat_prompt(..., simplify=simplify)`
    - _Requirements: 8.2, 8.3_

- [ ] 3. Checkpoint — Verify backend prompt rewrites compile and existing tests pass
  - Run `pytest` in `backend/`, ensure `test_analysis.py`, `test_conflict.py`, `test_chat.py` still pass since output shapes are unchanged. Ask the user if failures arise.

- [ ] 4. Backend: new endpoints — Quick Scan and Snap & Check
  - [ ] 4.1 Implement quick-scan router
    - Create `backend/routers/quick_scan.py` with `POST /quick-scan` following the existing router injection pattern (module-level `_llm_service` set in `main.py` startup)
    - Validate `claim` (non-empty, max 500 chars) → HTTP 422 with `ErrorResponse` on failure (Property 4)
    - Call `LLMService.complete()` with `build_quick_scan_prompt`, parse response via the existing `_strip_json_fences` + `json.loads` pattern with a fallback `QuickScanResponse` (confidence `"LOW"`) on parse failure — never raise 500
    - Apply `@limiter.limit("10/minute")` matching the existing `/api/chat` rate limit
    - Register the router in `main.py` (`app.include_router(quick_scan.router, prefix="/api", tags=["quick-scan"])`) and inject `_llm_service` in the startup event alongside the other router injections
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 10.5_

  - [ ] 4.2 Implement vision completion method in LLMService
    - Add `complete_vision(system_prompt, user_text, image_base64, image_mime, max_tokens=800)` to `backend/services/llm_service.py`, reusing `self._client` and `self._semaphore`, using the OpenAI-compatible multi-part vision message format
    - Raise `LLMParseError("FIREWORKS_MODEL_VISION not configured")` if `self._model_vision` is empty (Property 5)
    - _Requirements: 7.2, 11.2_

  - [ ] 4.3 Implement vision chat route
    - Add `POST /chat/vision` to `backend/routers/chat.py` accepting multipart `UploadFile` (image) + form fields `sessionId` and optional `question`
    - Validate image MIME type (`image/png`, `image/jpeg`, `image/jpg`, `image/webp`) and size (≤10MB) → HTTP 422 with `ErrorResponse` on failure, mirroring `routers/upload.py`'s validation pattern
    - On success, base64-encode the image, call `complete_vision`, wrap the result into a `StructuredAIResponse`-shaped answer (reuse existing JSON parsing helpers where the vision model returns structured JSON, or wrap plain text into `{answer: text, evidence: [], risks: "", recommendation: ""}` if not JSON), and return a `ChatResponse` matching the existing shape
    - IF `FIREWORKS_MODEL_VISION` is not configured OR the Fireworks call fails, return a graceful fallback `ChatResponse` explaining the limitation rather than a 500 (Property 5)
    - _Requirements: 7.1, 7.3, 7.4, 7.5, 10.5, 11.2_

- [ ] 5. Backend: demo documents replacement
  - [ ] 5.1 Create new demo sample documents
    - Create `sample_documents/Demo_EcoTechCorp_SustainabilityReport.txt` containing a fictional "EcoTech Corp" report with a carbon-neutrality claim that only accounts for Scope 1 emissions, omitting Scope 2/3
    - Create `sample_documents/Demo_EcoTechCorp_PackagingClaims.txt` containing contradicting packaging/marketing claims (e.g., "100% recycled materials", "carbon neutral by 2025") not fully supported by the report
    - _Requirements: 9.1_

  - [ ] 5.2 Update demo router to use new documents
    - Update `backend/routers/demo.py` to reference the new sample documents and ensure the pre-computed/pre-analyzed demo response includes at least 1 conflict, at least 3 risks, and a `greenwashScore` in the 0-30 band
    - Update the demo's pre-seeded chat messages (`preSeededMessages`) to reflect sustainability-claim Q&A consistent with the new content
    - _Requirements: 9.2, 9.3, 9.4_

- [ ] 6. Checkpoint — Verify new backend endpoints and demo data
  - Manually call `POST /api/quick-scan` with a valid claim, an empty claim, and a 501-char claim; verify `GET /api/demo` returns conflicts/risks/greenwashScore per Requirement 9. Ask the user if issues arise.

- [ ] 7. Frontend: types, API functions, design tokens
  - [ ] 7.1 Add additive frontend types
    - Add `greenwashScore?: number` to the `Analysis` interface in `frontend/src/lib/types.ts`
    - Add new `QuickScanResponse` interface (`verdict: string`, `whatToLookFor: string[]`, `confidence: 'LOW'|'MEDIUM'|'HIGH'`)
    - _Requirements: 2.4, 10.2_

  - [ ] 7.2 Add new API functions
    - Add `quickScan(claim: string): Promise<QuickScanResponse>` to `frontend/src/lib/api.ts` following the existing fetch/error-handling pattern
    - Add `sendVisionMessage(sessionId: string, image: File, question?: string): Promise<ChatResponse>` to `frontend/src/lib/api.ts` using multipart `FormData`, following the existing `uploadDocuments` pattern for file submission and error handling
    - _Requirements: 6.6, 7.6, 10.1_

  - [ ] 7.3 Apply GreenLens design tokens
    - Replace/extend `frontend/src/styles/theme.css` with the GreenLens token set from `.kiro/steering/greenlens-design-system.md`: `--ink`, `--lead`, `--graphite`, `--rule`, `--ash`, `--ghost`, `--leaf`, `--leaf-dim`, `--leaf-border`, `--paper`, `--parchment`, `--flag-red`, `--flag-amber`, `--flag-blue`, and their `-dim` variants
    - Preserve `--amd-signal: #ED1C24` unchanged, used only by `AMDBadge`
    - If the `greenlens-ui-redesign` spec has already been implemented (Syne/IBM Plex fonts loaded, `--volt` etc. in place), replace `--volt`/`--volt-dim`/`--volt-border` references with `--leaf`/`--leaf-dim`/`--leaf-border`; if not yet implemented, also add the Google Fonts `<link>` for Syne/IBM Plex Sans/IBM Plex Mono to `frontend/index.html` per that spec's Requirement 1.6
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 8. Frontend: new shared components
  - [ ] 8.1 Create GreenwashScoreGauge component
    - Create `frontend/src/app/components/GreenwashScoreGauge.tsx` accepting `{ score?: number }`, rendering a neutral state when `score` is `undefined`/`null`, and the correct band color/label per the design document's band logic (0-30 red, 31-60 amber, 61-100 leaf-green)
    - _Requirements: 2.5, 2.6_

  - [ ] 8.2 Create ClaimVsRealityRow component
    - Create `frontend/src/app/components/ClaimVsRealityRow.tsx` accepting `{ row: ComparisonRow }`, rendering two columns keyed by `"They Say"` (`--paper` background) and `"Data Shows"` (`--parchment` background)
    - _Requirements: 4.4_

  - [ ] 8.3 Update Badges.tsx label/color mapping
    - Update `RiskBadge` in `frontend/src/app/components/Badges.tsx` to render `MISLEADING`/`--flag-red` for `HIGH`, `VAGUE`/`--flag-amber` for `MEDIUM`, `UNVERIFIED`/`--flag-blue` for `LOW`, without changing the component's prop interface (Property 3)
    - _Requirements: 4.1_

  - [ ] 8.4 Update ConflictAlert → ContradictionAlert styling
    - Update the existing conflict-alert rendering (in `Dashboard.tsx`/`Demo.tsx` or a shared component if factored out) to display header text "CONTRADICTION DETECTED" and use `--flag-red` instead of `--amd-signal` for the left border and label color, preserving the existing conditional-render-on-`conflicts.length > 0` behavior
    - _Requirements: 4.2, 4.3_

  - [ ] 8.5 Create QuickScanPanel component
    - Create `frontend/src/app/components/QuickScanPanel.tsx` — self-contained (local `useState` only, no session/global state), with a textarea, submit button, and rendered `verdict`/`whatToLookFor`/`confidence` result using `quickScan()`
    - _Requirements: 6.5_

- [ ] 9. Checkpoint — Verify new components compile
  - Run `tsc --noEmit` in `frontend/`. Ask the user if errors arise.

- [ ] 10. Frontend: page rebrand — Landing, Dashboard, Chat, Demo
  - [ ] 10.1 Rebrand Landing.tsx
    - Update headline, subheadline, stats-row, and hackathon-badge copy to sustainability-claim-verification framing, preserving all existing upload/drag-drop/analyze-button logic and the `getBenchmarkSpeedup` call unchanged
    - Mount `QuickScanPanel` alongside the existing upload zone
    - _Requirements: 5.1, 5.2, 6.5_

  - [ ] 10.2 Rebrand Dashboard.tsx
    - Update card titles/labels ("Comparison Matrix" → "Claim vs. Reality"), mount `GreenwashScoreGauge` above `AnalysisCardGrid` using `analysis.greenwashScore`, replace comparison-matrix table rendering with `ClaimVsRealityRow` per row
    - Preserve sidebar document-list rendering, session/export button wiring, and all existing state/API calls unchanged
    - _Requirements: 2.5, 4.4, 5.3_

  - [ ] 10.3 Rebrand Chat.tsx
    - Update AI persona introduction copy and quick-question chip suggestions to sustainability-claim topics
    - Add ELI15 toggle pill in the chat header (local state `simplify`, included in chat request bodies)
    - Add camera/attach control to the input bar (`<input type="file" accept="image/*" capture="environment">`), rendering an attached-image thumbnail chip; on send with an attached image, call `sendVisionMessage()` instead of `streamChatMessage()` and clear the attachment after sending
    - Preserve existing SSE streaming logic, message history state, and evidence-section rendering structure for standard (non-vision) messages
    - _Requirements: 5.4, 7.6, 7.7, 8.1, 8.2_

  - [ ] 10.4 Rebrand Demo.tsx
    - Update copy and card rendering to match the Dashboard rebrand (score gauge, claim vs. reality rows, contradiction alert labels)
    - Update pre-seeded chat message copy to reflect the new EcoTech Corp demo content
    - Preserve the `getDemoData()` call signature and `DemoResponse` shape consumption unchanged
    - _Requirements: 5.5, 9.4_

  - [ ] 10.5 Rebrand NavigationBar wordmark
    - Update the logo mark in `frontend/src/app/components/NavigationBar.tsx` from "Clausify"+"AI" to "GreenLens" ("Green" default text color, "Lens" in Syne 700 colored `--leaf`)
    - _Requirements: 3.5_

- [ ] 11. Checkpoint — Verify all pages compile and render
  - Run `tsc --noEmit` and `npm run build` in `frontend/`. Ask the user if errors arise.

- [ ] 12. Verification and cleanup
  - [ ] 12.1 Verify additive-only backend model changes
    - Confirm `Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `UploadResponse`, `AnalyzeResponse`, `ChatResponse`, `ErrorResponse` in `backend/models/response.py` have no removed or renamed fields versus the pre-pivot version
    - _Requirements: 10.3_

  - [ ] 12.2 Verify additive-only frontend type changes
    - Confirm all existing fields in `frontend/src/lib/types.ts` are unchanged; only `greenwashScore?` was added to `Analysis` and `QuickScanResponse` was added as a new interface
    - _Requirements: 10.2_

  - [ ] 12.3 Verify API function signature preservation
    - Confirm `uploadDocuments()`, `analyzeDocuments()`, `streamChatMessage()`, `exportReport()`, `getDemoData()`, `getSuggestedQuestions()` signatures in `frontend/src/lib/api.ts` are unchanged
    - _Requirements: 10.1_

  - [ ] 12.4 Verify AMD signal color isolation
    - Grep for `--amd-signal` usage — confirm it appears only in `AMDBadge`, never in `RiskBadge`/`ContradictionAlert`/`GreenwashScoreGauge`
    - Grep for `#ED1C24` and `#F04452` — confirm they are never used interchangeably for the same element
    - _Requirements: 3.2_

  - [ ]* 12.5 Write backend property tests
    - **Property 1: Greenwash Score is always clamped to [0, 100]**
    - **Property 2: Missing or non-numeric score falls back to 50**
    - **Property 4: Quick Scan rejects invalid claims and never crashes**
    - **Property 5: Vision endpoint availability is determined solely by configuration**
    - **Property 6: ELI15 flag defaults to False and never breaks output shape**
    - **Validates: Requirements 2.2, 2.3, 6.1, 6.3, 7.5, 8.3, 8.4, 11.2**

  - [ ]* 12.6 Write frontend property test
    - **Property 3: Risk level to Greenwash Flag label/color mapping is total and exclusive**
    - **Validates: Requirements 4.1**

  - [ ] 12.7 Run full existing backend test suite
    - Run `pytest` in `backend/` and confirm `test_analysis.py`, `test_chat.py`, `test_conflict.py`, `test_embedding.py`, `test_error_format.py`, `test_session.py`, `test_upload.py` all still pass
    - _Requirements: 10.4_

- [ ] 13. Final checkpoint — Ensure all tests pass and demo works end-to-end
  - Run backend `pytest`, frontend `tsc --noEmit` and `npm run build`; manually exercise: upload → analyze → view Greenwash Score/flags/contradiction/claim-vs-reality on Dashboard, Quick Scan on Landing, ELI15 toggle + Snap & Check in Chat, and the Demo page. Ask the user if issues arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery given the hackathon timeline
- If the `greenlens-ui-redesign` spec has not yet been implemented when starting this pivot, Task 7.3 must also perform the font-loading and base-token work from that spec's Task 1, since GreenLens's design system is layered on top of it
- Prompt rewrite tasks (2.1-2.8) preserve every JSON output contract exactly — this is the core guarantee that lets the rest of the pipeline (parsing, models, frontend rendering) remain untouched
- Reference `.kiro/steering/greenlens-master-plan.md` for the overall feature roadmap and priority ordering if time runs short — Quick Scan and Snap & Check (Tasks 4, 7.2, 8.5, 10.3) are marked "high-value" but not "must-have" in that plan

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"] },
    { "id": 2, "tasks": ["2.8"] },
    { "id": 3, "tasks": ["4.1", "4.2"] },
    { "id": 4, "tasks": ["4.3", "5.1"] },
    { "id": 5, "tasks": ["5.2"] },
    { "id": 6, "tasks": ["7.1", "7.3"] },
    { "id": 7, "tasks": ["7.2", "8.1", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 8, "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5"] },
    { "id": 9, "tasks": ["12.1", "12.2", "12.3", "12.4", "12.7"] },
    { "id": 10, "tasks": ["12.5", "12.6"] }
  ]
}
```
