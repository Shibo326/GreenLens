---
inclusion: manual
---

# GreenLens — Master Pivot Plan

> Reference this steering file with `#greenlens-master-plan` whenever working on the pivot. See also `#greenlens-design-system` for tokens/components and the spec at `.kiro/specs/greenlens-pivot/`.

## What This Is

GreenLens is an AI-powered greenwashing/sustainability-claims detection platform built for the YFS Build for Good Hackathon. It started life as "Clausify," an enterprise procurement-analysis tool built for a different hackathon, and has been fully rebranded end-to-end (code, prompts, UI, docs). Same underlying tech stack (FastAPI + React + Fireworks AI on AMD MI300X + ChromaDB RAG pipeline), repointed from "enterprise procurement conflict detection" to "consumer greenwashing detection." Track: **AI for Sustainability**.

**As of this writing, the full codebase-wide rebrand from Clausify → GreenLens is complete** — brand names, log messages, prompts, PDF reports, storage keys, and UI copy all say "GreenLens." Any "Clausify" string found in `backend/` or `frontend/src/` outside of `Feature: clausify-ui-redesign` test-traceability comments is a regression bug, not expected state.

**One-liner:** Upload a company's sustainability claims (report, packaging, marketing) → AI cross-references claims against data and flags contradictions, vague language, and misleading claims in under 90 seconds.

---

## Rebrand Mapping (Concept-Level)

| Clausify Concept | → | GreenLens Concept |
|---|---|---|
| Procurement document conflict | → | Greenwashing contradiction |
| Billing discrepancy | → | Claim vs. reality mismatch |
| Risk (HIGH/MEDIUM/LOW) | → | Greenwash Flag (MISLEADING/VAGUE/UNVERIFIED) |
| Comparison Matrix (vendor vs vendor) | → | Claim vs Reality Matrix |
| Executive Summary | → | Sustainability Verdict + Greenwash Score (0-100) |
| Recommendation | → | Accountability Action Steps |
| Chat Copilot (procurement analyst persona) | → | Sustainability Analyst persona (+ ELI15 simplification toggle) |
| Conflict severity (HIGH/MED/LOW) | → | Same enum, remapped labels for greenwash context |
| AMD MI300X branding | → | **Kept as-is** — still the technical differentiator, still true |

## Code Reuse Assessment (Confirmed From Codebase Read)

- `models/response.py` — `Risk`, `Conflict`, `ComparisonRow`, `Recommendation`, `AnalysisResult` structures are domain-agnostic. **Reused as-is**, only add a `greenwashScore` field to `AnalysisResult`.
- `services/analysis_service.py` — orchestration (5 parallel `asyncio.gather` calls, timeout wrapping, fallback handling) is 100% reusable. Only the prompt *content* passed to `llm_service.complete()` changes.
- `services/conflict_engine.py` — conflict detection engine reused unchanged at the code level; only `prompts/conflict_detection.py` text changes.
- `services/llm_service.py`, `embedding_service.py`, `vector_store.py`, `session_manager.py`, `document_parser.py`, `pdf_generator.py` — **zero changes needed**.
- `routers/upload.py`, `report.py` — **zero changes needed**.
- `routers/analyze.py`, `chat.py` — minor additions only (new `/api/quick-scan` and vision support in `/api/chat`), existing logic untouched.
- Frontend `api.ts`, `store.tsx`, `types.ts` — **preserved**, same constraint as the UI redesign spec. New fields are additive (optional), not breaking.
- Frontend pages (`Landing`, `Dashboard`, `Chat`, `Demo`) — full visual rebrand + copy changes, structural logic (state, API calls) preserved.

**Estimated reuse: ~85%** — confirmed by reading actual files, not estimated blind.

---

## Feature Roadmap (Priority Order)

### Must-have (Core Pivot)
1. Rebrand tokens + typography (green palette — see design-system steering)
2. Rewrite 5 prompts: system persona, greenwash detection, greenwash flags, sustainability verdict + score, action steps
3. Greenwash Score (0-100) — new field on `AnalysisResult`, color-coded gauge on Dashboard
4. New demo documents (EcoTech Corp sustainability report + contradicting packaging claims)
5. Landing/Dashboard/Chat/Demo page rebrand (copy + visual)

### High-value additions
6. **Snap & Check** — vision-capable chat: user attaches/photographs a product label, AI reads + analyzes claims directly (needs a vision model call — see `greenlens-vision-integration` agent)
7. **Quick Scan** — text-only entry point: type a claim ("Is 'carbon neutral by 2030' meaningful?") and get an instant mini-verdict without uploading anything
8. **ELI15 mode** — chat toggle that simplifies AI language for a 14-18 year old audience
9. Known-greenwashers reference context — small curated dataset of real fined/documented greenwashing cases, injected into prompts for grounded comparisons

### Nice-to-have (time permitting)
10. Mobile-first pass + PWA manifest (add to home screen, camera-first upload)
11. Share card export (OG image with Greenwash Score for social sharing)
12. Multi-language output (prompts already support language-matching pattern from `chat_copilot.py` — extend it)

---

## Timeline (5-7 Days)

| Day | Focus |
|---|---|
| 1 | Rebrand tokens/fonts, rewrite system prompt + greenwash detection prompt |
| 2 | Rewrite remaining 4 prompts, add `greenwashScore` model field, demo documents |
| 3 | Landing + Dashboard rebrand (copy, Greenwash Score gauge, Claim vs Reality matrix) |
| 4 | Chat rebrand + ELI15 toggle + Quick Scan endpoint/UI |
| 5 | Snap & Check vision integration |
| 6 | Mobile-first pass, PWA manifest, polish |
| 7 | Buffer — bug fixes, Loom video, pitch deck |

---

## What We Are NOT Doing

- **No native APK.** PWA (Add to Home Screen) covers the mobile use case with 10x less work — see prior conversation reasoning.
- **No plant/tree identification.** Out of scope, dilutes the pitch focus. Vision use is strictly for reading product labels/packaging claims.
- **No new MCP server.** Nothing here requires an external tool integration Kiro doesn't already have (web_fetch/web_search cover any future URL-scanning feature; no live automation dependency needed for the hackathon scope).

---

## Related Documents

- `.kiro/steering/greenlens-design-system.md` — colors, typography, component specs
- `.kiro/specs/greenlens-pivot/requirements.md` — EARS requirements
- `.kiro/specs/greenlens-pivot/design.md` — technical design
- `.kiro/specs/greenlens-pivot/tasks.md` — implementation plan
- `.kiro/steering/yfs-hackathon-analysis.md` — original hackathon fit analysis and rubric (historical — led to this pivot)
- `.kiro/agents/greenlens-vision-integration.md` — agent for the Snap & Check feature
