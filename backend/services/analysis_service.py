import asyncio
import json
import logging
import os
from datetime import datetime

from models.document import Chunk
from models.response import (
    AnalysisResult,
    ComparisonRow,
    Recommendation,
    Risk,
    SourceLink,
)
from prompts.recommendation import build_recommendation_prompt
from prompts.risk_analysis import build_risk_prompt
from prompts.system_prompt import get_system_prompt
from services.conflict_engine import ConflictEngine
from services.llm_service import LLMService, LLMParseError, _strip_json_fences
from services.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Timeout for individual LLM calls (seconds)
# deepseek-v4-pro reasoning model needs generous time for multi-doc analysis
LLM_CALL_TIMEOUT = 180

# Prompt for comparison matrix — Claim vs Reality analysis for greenwashing detection
COMPARISON_MATRIX_PROMPT = """Based on the document content above, create a Claim vs. Reality comparison matrix that exposes gaps between what the company SAYS and what the DATA SHOWS.

REASONING STEPS (follow internally):
1. What sustainability/environmental CLAIMS are made in marketing, packaging, or public communications?
2. What does the actual DATA (sustainability reports, audit results, emissions figures) show for each claim?
3. For each row, which side — the claim or the data — is more credible, and what's the gap?

HOW TO BUILD EACH ROW:
- "field": The sustainability topic being examined (e.g., "Carbon Neutrality Claim", "Recycled Content", "Water Usage Reduction")
- "values" must contain exactly two keys: "They Say" (the marketing/packaging claim) and "Data Shows" (what the report/data actually reveals)
- "winner": Which side is more credible — "They Say" if claim is well-supported, "Data Shows" if data contradicts/undermines the claim, or null if inconclusive

WHAT TO COMPARE:
- Emissions claims vs. reported Scope 1/2/3 data
- "Recycled" / "Recyclable" claims vs. actual material composition or recycling rate data
- "Net zero" / "Carbon neutral" targets vs. actual offset quality and coverage
- Certification claims vs. what the certification actually covers
- Packaging claims vs. product lifecycle data
- "Natural" / "Organic" claims vs. ingredient/sourcing data
- Reduction targets vs. baseline year and actual progress

WINNER SELECTION RULES:
- "Data Shows" wins when data contradicts or significantly undermines the marketing claim
- "They Say" wins when the claim is specific, measurable, and fully supported by data
- null when evidence is insufficient to determine credibility either way

Return ONLY valid JSON in this exact format:
{{
  "comparisonMatrix": [
    {{
      "field": "<specific sustainability topic being examined — not generic labels like 'Environment' but rather 'Carbon Offset Coverage (% of total emissions)'>",
      "values": {{
        "They Say": "<exact marketing/packaging claim or paraphrased assertion from the company>",
        "Data Shows": "<what the sustainability report, audit, or data actually reveals>"
      }},
      "winner": "<'They Say' if claim is credible, 'Data Shows' if data contradicts claim, or null if inconclusive>"
    }}
  ]
}}

Include 5-8 comparison rows based on the most significant claim-vs-reality gaps found.
Every value must be grounded in document content. Flag inferences with (inferred) or (not explicitly stated).
Do NOT include any text outside the JSON object."""


class AnalysisService:
    """
    Orchestrates the full multi-document AI analysis pipeline.

    Performance-optimized architecture:
    - Tiered model routing: deepseek-v4-pro for reasoning, deepseek-v4-flash for structured tasks
    - SINGLE_CALL_MODE: combine all analysis into 1 call (set SINGLE_CALL_MODE=true in env)
    - All 5 LLM calls run in parallel (no batching)
    - Web research enrichment: real-time online data to cross-reference claims
    - Suggested questions merged into executive summary call (saves 1 call)
    - Conflict detection consolidated to 1 call for ALL docs (saves N*(N-1)/2 - 1 calls)
    - Per-call timeout of 80s with graceful partial results
    - Token budgets tuned per call type

    Total LLM calls: 5 parallel (was 6+ sequential/batched, up to 34 with pairwise conflicts)
    SINGLE_CALL_MODE: 1 call total (emergency speed fallback)
    """

    def __init__(
        self,
        llm_service: LLMService,
        conflict_engine: ConflictEngine,
        session_manager: SessionManager,
    ):
        self.llm_service = llm_service
        self.conflict_engine = conflict_engine
        self.session_manager = session_manager
        self._single_call_mode = os.getenv("SINGLE_CALL_MODE", "false").lower() == "true"

    async def run_full_analysis(
        self,
        session_id: str,
        chunks: list[Chunk],
        doc_names: list[str],
    ) -> AnalysisResult:
        """
        Run the complete analysis pipeline.

        Normal mode: 5 parallel LLM calls (tiered models).
        SINGLE_CALL_MODE: 1 mega LLM call (extreme speed, lower quality).

        Target: <35s wall time for 2 documents in normal mode.
        """
        system_prompt = get_system_prompt(doc_names)

        if self._single_call_mode:
            mode_reason = "SINGLE_CALL_MODE env"
            logger.info(
                f"[SINGLE_CALL_MODE] Starting single-mega-call analysis for session {session_id} "
                f"({len(chunks)} chunks, {len(doc_names)} documents) — reason: {mode_reason}"
            )
            return await self._run_single_call_analysis(session_id, system_prompt, chunks, doc_names)

        logger.info(
            f"Starting full analysis for session {session_id} "
            f"({len(chunks)} chunks, {len(doc_names)} documents) — 5 parallel LLM calls "
            f"[quality: deepseek-v4-pro, fast: deepseek-v4-flash, timeout: {LLM_CALL_TIMEOUT}s]"
        )

        if chunks:
            logger.debug(f"First chunk: {chunks[0].source_document} ({len(chunks)} chunks)")
        else:
            logger.warning("No document chunks — extraction may have failed")

        # --- Fetch web context for richer analysis (runs before parallel calls) ---
        web_context = ""
        web_sources: list[SourceLink] = []
        try:
            from services import web_search
            # Extract company/topic from document names for targeted search
            company_hint = " ".join(
                name.replace(".pdf", "").replace("_", " ").replace("-", " ")
                for name in doc_names[:2]
            )[:100]
            web_context, raw_sources = await web_search.search_with_sources(
                f"greenwashing {company_hint} sustainability claims"
            )
            web_sources = [
                SourceLink(title=s["title"], url=s["url"], snippet=s["snippet"])
                for s in raw_sources
            ]
        except Exception as e:
            logger.warning(f"[analysis] Web search failed (non-fatal): {e}")
            web_context = ""
            web_sources = []

        # --- Run analysis calls with rate-limit-safe staggering ---
        # Phase 1: Summary + Risks (most important — run first)
        (
            summary_and_questions_result,
            risks_result,
        ) = await asyncio.gather(
            self._with_timeout(
                self._generate_summary_and_questions(system_prompt, chunks, web_context=web_context),
                "summary+questions",
            ),
            self._with_timeout(
                self._generate_risks(system_prompt, chunks, web_context=web_context),
                "risks",
            ),
            return_exceptions=True,
        )

        # Brief pause to avoid rate limit burst on Fireworks
        await asyncio.sleep(1)

        # Phase 2: Matrix + Recommendation + Conflicts (secondary)
        (
            matrix_result,
            recommendation_result,
            conflicts_result,
        ) = await asyncio.gather(
            self._with_timeout(
                self._generate_comparison_matrix(system_prompt, chunks, doc_names, web_context=web_context),
                "comparison_matrix",
            ),
            self._with_timeout(
                self._generate_recommendation(system_prompt, chunks, web_context=web_context),
                "recommendation",
            ),
            self._with_timeout(
                self.conflict_engine.detect(chunks, doc_names),
                "conflicts",
            ),
            return_exceptions=True,
        )

        # Unpack summary + questions + greenwashScore
        if isinstance(summary_and_questions_result, Exception):
            logger.warning(f"Summary generation failed, using fallback: {summary_and_questions_result}")
            summary_result = f"Analysis of {len(doc_names)} document(s): {', '.join(doc_names)}. The AI summary could not be generated — please review individual sections below for detailed findings."
            suggested_questions = ["What are the key claims?", "Are there any greenwash flags?", "What contradictions exist?"]
            greenwash_score = None
        else:
            summary_result, suggested_questions, greenwash_score = summary_and_questions_result

        if isinstance(risks_result, Exception):
            logger.warning(f"Risk analysis failed, using empty: {risks_result}")
            risks_result = []

        if isinstance(matrix_result, Exception):
            logger.warning(f"Comparison matrix failed, using empty: {matrix_result}")
            matrix_result = []

        if isinstance(recommendation_result, Exception):
            logger.warning(f"Recommendation failed, using fallback: {recommendation_result}")
            recommendation_result = Recommendation(
                title="Analysis Incomplete",
                summary="The AI analysis could not be fully completed. This may be due to API limits or service issues. Please try again.",
                nextSteps=["Retry the analysis", "Check if documents contain readable text", "Try uploading fewer documents"],
                confidence=0.3,
            )

        if isinstance(conflicts_result, Exception):
            logger.warning(f"Conflict detection failed, using empty: {conflicts_result}")
            conflicts_result = []

        analysis = AnalysisResult(
            analyzedAt=datetime.utcnow(),
            executiveSummary=summary_result,
            greenwashScore=self._clamp_greenwash_score(greenwash_score, risks=risks_result, matrix=matrix_result),
            risks=risks_result,
            comparisonMatrix=matrix_result,
            conflicts=conflicts_result,
            recommendation=recommendation_result,
            suggestedQuestions=suggested_questions,
            sources=web_sources,
        )

        self.session_manager.store_analysis(session_id, analysis)
        logger.info(f"Analysis complete for session {session_id}")
        return analysis

    async def _run_single_call_analysis(
        self,
        session_id: str,
        system_prompt: str,
        chunks: list[Chunk],
        doc_names: list[str],
    ) -> AnalysisResult:
        """
        Emergency speed fallback: all analysis in ONE LLM call.
        Activated by SINGLE_CALL_MODE=true env var.
        """
        from prompts.executive_summary import _format_chunks
        context = _format_chunks(chunks)

        try:
            data = await asyncio.wait_for(
                self.llm_service.single_mega_call(system_prompt, context, doc_names),
                timeout=LLM_CALL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise LLMParseError(f"Single mega-call timed out after {LLM_CALL_TIMEOUT}s")

        # Parse each field with graceful fallbacks
        summary = data.get("executiveSummary", "Analysis complete.")

        risks = []
        for i, item in enumerate(data.get("risks", [])):
            try:
                if isinstance(item, dict):
                    item = {
                        "id": item.get("id", f"r{i+1}"),
                        "level": item.get("level", "MEDIUM").upper(),
                        "description": item.get("description", ""),
                        "sourceDocument": item.get("sourceDocument", ""),
                        "category": item.get("category", "Operational"),
                    }
                risks.append(Risk(**item))
            except Exception as e:
                logger.warning(f"[single-call] Skipping malformed risk: {e}")

        matrix = []
        for item in data.get("comparisonMatrix", []):
            try:
                matrix.append(ComparisonRow(**item))
            except Exception as e:
                logger.warning(f"[single-call] Skipping malformed matrix row: {e}")

        recommendation = Recommendation(
            title="Analysis Complete",
            summary="Please review the risks and comparison matrix for details.",
            nextSteps=["Review identified risks", "Compare claims vs. data", "Ask the AI Copilot"],
            confidence=0.6,
        )
        rec_data = data.get("recommendation")
        if rec_data and isinstance(rec_data, dict):
            try:
                recommendation = Recommendation(**rec_data)
            except Exception as e:
                logger.warning(f"[single-call] Recommendation parse failed: {e}")

        questions = data.get("suggestedQuestions", [])
        if not isinstance(questions, list):
            questions = []
        questions = [q for q in questions if isinstance(q, str)][:6]

        # Conflict detection still separate (needs doc grouping logic)
        conflicts = []
        raw_conflicts = data.get("conflicts", [])
        if not raw_conflicts and len(doc_names) >= 2:
            # Run conflict detection as a separate fast call
            try:
                conflicts = await asyncio.wait_for(
                    self.conflict_engine.detect(chunks, doc_names),
                    timeout=LLM_CALL_TIMEOUT,
                )
            except Exception as e:
                logger.warning(f"[single-call] Conflict detection failed: {e}")

        # Extract and clamp greenwashScore
        greenwash_score = self._clamp_greenwash_score(data.get("greenwashScore"), risks=risks, matrix=matrix)

        analysis = AnalysisResult(
            analyzedAt=datetime.utcnow(),
            executiveSummary=summary,
            greenwashScore=greenwash_score,
            risks=risks,
            comparisonMatrix=matrix,
            conflicts=conflicts,
            recommendation=recommendation,
            suggestedQuestions=questions,
        )
        self.session_manager.store_analysis(session_id, analysis)
        logger.info(f"[SINGLE_CALL_MODE] Analysis complete for session {session_id}")
        return analysis

    async def _with_timeout(self, coro, label: str):
        """Wrap a coroutine with a timeout. Returns the exception on timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=LLM_CALL_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM call '{label}' timed out after {LLM_CALL_TIMEOUT}s"
            )
            raise LLMParseError(
                f"LLM call '{label}' timed out after {LLM_CALL_TIMEOUT}s"
            )

    @staticmethod
    def _format_chunks_generous(chunks: list["Chunk"]) -> str:
        """
        Format chunks with generous limits for the executive summary call.
        Single-doc gets up to 8 chunks at 1200 chars for deeper analysis.
        Multi-doc gets up to 4 chunks per doc at 1000 chars.
        """
        if not chunks:
            return "(no document content available)"

        unique_docs = list(dict.fromkeys(c.source_document for c in chunks))
        num_docs = len(unique_docs)
        if num_docs == 1:
            effective_max = 8
            max_chars = 1200
        elif num_docs == 2:
            effective_max = 5
            max_chars = 1000
        else:
            effective_max = 4
            max_chars = 900

        sections = []
        current_doc = None
        doc_chunk_count: dict[str, int] = {}
        for chunk in chunks:
            doc = chunk.source_document
            count = doc_chunk_count.get(doc, 0)
            if count >= effective_max:
                continue
            doc_chunk_count[doc] = count + 1
            if doc != current_doc:
                current_doc = doc
                sections.append(f"\n=== {current_doc} ===")
            sections.append(chunk.text[:max_chars])
        return "\n".join(sections)

    @staticmethod
    def _clamp_greenwash_score(raw_score, risks=None, matrix=None) -> int | None:
        """
        Clamp greenwashScore to [0, 100].

        When the LLM doesn't provide a score (None or non-numeric), compute a
        data-driven fallback from available analysis results instead of defaulting
        to an arbitrary 50:
        - If risks were detected: score = 30 (suspicious)
        - If comparison matrix has contradictions ("Data Shows" wins): lower further
        - If no data at all: return None (frontend shows "Unable to determine")
        """
        if raw_score is not None:
            try:
                score = int(raw_score)
                return max(0, min(100, score))
            except (TypeError, ValueError):
                logger.warning(f"[greenwashScore] Non-numeric value '{raw_score}', computing from data")

        # --- Data-driven fallback ---
        has_risks = risks and len(risks) > 0
        has_contradictions = False

        if matrix:
            for row in matrix:
                # Check if "Data Shows" won (meaning claim is contradicted)
                winner = getattr(row, "winner", None) if hasattr(row, "winner") else (row.get("winner") if isinstance(row, dict) else None)
                if winner and "data" in str(winner).lower():
                    has_contradictions = True
                    break

        if not has_risks and not has_contradictions:
            # No evidence of issues — can't determine a score
            logger.warning("[greenwashScore] Missing from LLM and no data to compute fallback, returning None")
            return None

        # Start at 30 (suspicious) if risks exist
        score = 30 if has_risks else 50

        # Lower further if matrix shows contradictions
        if has_contradictions:
            score -= 10

        # More risks = lower score
        if has_risks:
            risk_count = len(risks) if risks else 0
            high_risk_count = sum(
                1 for r in (risks or [])
                if (getattr(r, "level", None) or (r.get("level") if isinstance(r, dict) else "")).upper() == "HIGH"
            )
            if high_risk_count >= 3:
                score -= 10
            elif risk_count >= 5:
                score -= 5

        logger.info(f"[greenwashScore] Computed data-driven fallback: {max(0, score)} (risks={has_risks}, contradictions={has_contradictions})")
        return max(0, min(100, score))
    async def _generate_summary_and_questions(
        self,
        system_prompt: str,
        chunks: list[Chunk],
        web_context: str = "",
    ) -> tuple[str, list[str], int | None]:
        """
        Generate executive summary, suggested questions, AND greenwashScore in a single LLM call.
        Uses the PREMIUM model (deepseek-v4-pro) for deep reasoning.
        Merging these saves one full LLM round-trip (10-60s).

        If web_context is provided, real-time online sources are cross-referenced
        to improve the accuracy of the verdict and greenwash score.
        """
        # Format chunks with generous limits — this is the most important call
        context = self._format_chunks_generous(chunks)
        doc_names = list(dict.fromkeys(c.source_document for c in chunks))
        doc_list = ", ".join(doc_names) if doc_names else "the uploaded document"

        web_block = f"\n{web_context}\n" if web_context else ""

        merged_prompt = f"""You are a senior sustainability claims analyst. Write a verdict summary for a consumer or watchdog based on these documents.

DOCUMENTS: {doc_list}

{context}
{web_block}
Lead with the overall sustainability credibility verdict. Flag the most serious greenwashing concern. Include specific claims vs. data comparisons. End with a clear recommended action for consumers. If real-time web research above corroborates or contradicts a claim, factor it into your verdict and cite it as "Web source:".

Also provide a Greenwash Score from 0-100:
- 0-30: HIGH RISK — multiple misleading claims, major contradictions with data
- 31-60: MEDIUM RISK — vague claims, some unverified assertions, partial evidence
- 61-100: LOW RISK — claims are specific, measurable, third-party verified, data-consistent

Also generate 5 short follow-up questions (max 10 words each) that a consumer or watchdog would most likely want to ask. Make them SPECIFIC to the document content — not generic questions like "Are these claims true?" but rather "Does their Scope 3 data support the net-zero claim?"

Return ONLY valid JSON (no preamble, no explanation, just the JSON object):
{{
  "executiveSummary": "<4-6 sentence sustainability verdict: overall credibility, most serious greenwash flag, specific claim-vs-data example, recommended consumer action>",
  "greenwashScore": <integer 0-100>,
  "suggestedQuestions": ["question1", "question2", "question3", "question4", "question5"]
}}

CRITICAL RULES:
- Do NOT include reasoning, thinking process, or internal analysis in the JSON values
- The executiveSummary must be a clean professional paragraph for consumers — NOT your thought process
- Do NOT start executiveSummary with "Let me think", "I'd say", "Based on my analysis", cost calculations, or meta-commentary
- Write the summary as a final published verdict, not a draft"""

        # Use QUALITY model (kimi-k2p6) — it produces clean JSON without reasoning artifacts.
        # deepseek-v4-pro often embeds reasoning text inside JSON values which corrupts output.
        raw = await self.llm_service.complete(
            system_prompt, merged_prompt, max_tokens=800, tier="quality"
        )
        raw = _strip_json_fences(raw)

        # Extra safety: if raw still starts with prose (not JSON), find the JSON block
        if raw and raw[0] not in ('{', '['):
            brace_idx = raw.find('{')
            if brace_idx != -1:
                raw = raw[brace_idx:raw.rfind('}') + 1]

        try:
            data = json.loads(raw)
            summary = data.get("executiveSummary", "")
            greenwash_score = data.get("greenwashScore")
            questions = data.get("suggestedQuestions", [])
            if not isinstance(questions, list):
                questions = []
            questions = [q for q in questions if isinstance(q, str)][:6]

            # Post-processing: strip reasoning artifacts from summary
            # deepseek models sometimes embed their thinking in the JSON value itself
            bad_starts = [
                "We are asked", "Let me", "I need to", "First,", "The document",
                "Based on my analysis", "I'd say", "Looking at", "Output must be",
                "We need to", "Let's analyze",
            ]
            if summary:
                for bs in bad_starts:
                    if summary.strip().startswith(bs):
                        # The entire summary is reasoning — use a generic fallback
                        logger.warning(f"[summary] LLM leaked reasoning into executiveSummary (starts with '{bs}'). Regenerating.")
                        summary = ""
                        break

            if not summary:
                # Fallback: ask the fast model for a clean summary
                try:
                    fallback_raw = await self.llm_service.complete(
                        system_prompt,
                        merged_prompt + "\n\nCRITICAL: Output ONLY the JSON. The executiveSummary must be a FINAL VERDICT paragraph, NOT your thinking process.",
                        max_tokens=600,
                        tier="fast",
                    )
                    fallback_raw = _strip_json_fences(fallback_raw)
                    if fallback_raw and fallback_raw[0] not in ('{', '['):
                        bi = fallback_raw.find('{')
                        if bi != -1:
                            fallback_raw = fallback_raw[bi:fallback_raw.rfind('}') + 1]
                    fallback_data = json.loads(fallback_raw)
                    summary = fallback_data.get("executiveSummary", "Analysis complete. Please review flags and recommendations below.")
                    if not greenwash_score:
                        greenwash_score = fallback_data.get("greenwashScore")
                    if not questions:
                        questions = fallback_data.get("suggestedQuestions", [])
                except Exception as fb_err:
                    logger.warning(f"[summary] Fallback also failed: {fb_err}")
                    summary = "Analysis complete. Please review the greenwash flags and recommendations below for detailed findings."

            return summary, questions, greenwash_score
        except json.JSONDecodeError:
            # JSON parsing completely failed — don't show raw reasoning to users
            logger.warning(f"[summary] JSON parse failed. Raw first 200: {raw[:200]!r}")
            return "Analysis complete. Please review the greenwash flags and recommendations below for detailed findings.", [], None

    async def _generate_risks(
        self,
        system_prompt: str,
        chunks: list[Chunk],
        web_context: str = "",
    ) -> list[Risk]:
        """Generate risk analysis list using the PREMIUM model (deepseek-v4-pro)."""
        user_prompt = build_risk_prompt(chunks, web_context=web_context)
        # Increased to 1500 tokens — deepseek-v4-pro is more verbose
        # and needs extra headroom to output 5-8 detailed risk items without truncation.
        # Temperature 0.0 for maximum consistency in risk identification.
        raw = await self.llm_service.complete(
            system_prompt, user_prompt, max_tokens=1500, temperature=0.0, tier="quality"
        )
        logger.info(f"[risks] raw LLM response: {len(raw)} chars, first 500: {raw[:500]!r}")
        raw = _strip_json_fences(raw)
        logger.info(f"[risks] after strip, first 200: {raw[:200]!r}")

        import re as _re
        data = None

        # Strategy 1: direct parse
        try:
            data = json.loads(raw)
        except Exception:
            pass

        # Strategy 2: extract outermost { ... } block
        if data is None:
            brace_start = raw.find("{")
            brace_end = raw.rfind("}")
            if brace_start != -1 and brace_end > brace_start:
                try:
                    data = json.loads(raw[brace_start:brace_end + 1])
                except Exception:
                    pass

        # Strategy 3: fix trailing commas then retry
        if data is None:
            try:
                cleaned = _re.sub(r",\s*([}\]])", r"\1", raw)
                brace_start = cleaned.find("{")
                brace_end = cleaned.rfind("}")
                if brace_start != -1 and brace_end > brace_start:
                    data = json.loads(cleaned[brace_start:brace_end + 1])
            except Exception:
                pass

        # Strategy 4: extract just the risks array with regex
        if data is None:
            array_match = _re.search(r'"risks"\s*:\s*(\[.*?\])', raw, _re.DOTALL)
            if array_match:
                try:
                    risks_array = json.loads(array_match.group(1))
                    data = {"risks": risks_array}
                except Exception:
                    pass

        # Strategy 5: retry LLM with explicit JSON-only instruction
        if data is None:
            logger.warning(f"[risks] ALL parse strategies failed on first attempt — retrying with stricter prompt")
            retry_prompt = (
                user_prompt
                + "\n\nCRITICAL: Your previous response was not valid JSON. "
                "You MUST respond with ONLY a valid JSON object starting with { and ending with }. "
                "No preamble, no explanation, no markdown code fences. Start your response with { and end with }."
            )
            try:
                raw2 = await self.llm_service.complete(
                    system_prompt, retry_prompt, max_tokens=1500, tier="quality"
                )
                raw2 = _strip_json_fences(raw2)
                logger.info(f"[risks] retry response, first 200: {raw2[:200]!r}")
                try:
                    data = json.loads(raw2)
                except Exception:
                    brace_start = raw2.find("{")
                    brace_end = raw2.rfind("}")
                    if brace_start != -1 and brace_end > brace_start:
                        try:
                            cleaned2 = _re.sub(r",\s*([}\]])", r"\1", raw2[brace_start:brace_end + 1])
                            data = json.loads(cleaned2)
                        except Exception:
                            pass
            except Exception as retry_err:
                logger.warning(f"[risks] retry LLM call failed: {retry_err}")

        if data is None:
            logger.warning(f"[risks] ALL parse strategies failed including retry. Raw (500 chars): {raw[:500]!r}")
            return []

        risks_data = data.get("risks", []) if isinstance(data, dict) else []
        logger.info(f"[risks] parsed {len(risks_data)} risk items")

        # CONSISTENCY FIX: If the LLM returned valid JSON but zero risks,
        # and we have multi-document chunks (which almost always have discrepancies),
        # retry once with an even more explicit prompt.
        if not risks_data and len(set(c.source_document for c in chunks)) >= 2:
            logger.warning("[risks] Zero risks returned for multi-doc session — retrying with assertive prompt")
            retry_prompt = (
                user_prompt
                + "\n\nIMPORTANT: You returned zero risks, but these documents contain pricing discrepancies, "
                "conflicting terms, and/or financial exposure. This is INCORRECT. You MUST identify at least 3-5 risks. "
                "Look for: (1) price/amount differences between documents, (2) conflicting payment terms, "
                "(3) missing protections or one-sided clauses, (4) any term that could harm the buyer financially. "
                "Return the JSON with at least 3 risks. Start with {"
            )
            try:
                raw_retry = await self.llm_service.complete(
                    system_prompt, retry_prompt, max_tokens=1500, temperature=0.0, tier="quality"
                )
                raw_retry = _strip_json_fences(raw_retry)
                brace_s = raw_retry.find("{")
                brace_e = raw_retry.rfind("}")
                if brace_s != -1 and brace_e > brace_s:
                    raw_retry = raw_retry[brace_s:brace_e + 1]
                try:
                    retry_data = json.loads(raw_retry)
                    retry_risks = retry_data.get("risks", [])
                    if retry_risks:
                        risks_data = retry_risks
                        logger.info(f"[risks] Retry succeeded — got {len(risks_data)} risks")
                except json.JSONDecodeError:
                    cleaned_retry = _re.sub(r",\s*([}\]])", r"\1", raw_retry)
                    try:
                        retry_data = json.loads(cleaned_retry)
                        retry_risks = retry_data.get("risks", [])
                        if retry_risks:
                            risks_data = retry_risks
                            logger.info(f"[risks] Retry (cleaned) succeeded — got {len(risks_data)} risks")
                    except json.JSONDecodeError:
                        logger.warning("[risks] Retry also failed to parse")
            except Exception as retry_err:
                logger.warning(f"[risks] Retry LLM call failed: {retry_err}")

        risks = []
        for item in risks_data:
            try:
                # Normalize field names — Kimi/DeepSeek may use snake_case
                if isinstance(item, dict):
                    item = {
                        "id": item.get("id", f"r{len(risks)+1}"),
                        "level": item.get("level", item.get("severity", "MEDIUM")).upper(),
                        "description": item.get("description", item.get("content", "")),
                        "sourceDocument": item.get("sourceDocument", item.get("source_document", item.get("source", ""))),
                        "category": item.get("category", "Operational"),
                    }
                risks.append(Risk(**item))
            except Exception as e:
                logger.warning(f"Skipping malformed risk item: {e} — item keys: {list(item.keys()) if isinstance(item, dict) else type(item)}")
        return risks

    async def _generate_comparison_matrix(
        self,
        system_prompt: str,
        chunks: list[Chunk],
        doc_names: list[str],
        web_context: str = "",
    ) -> list[ComparisonRow]:
        """
        Generate comparison matrix rows.
        Uses FAST model (deepseek-v4-flash) — structured JSON output, no deep reasoning needed.
        max_tokens=1000 is sufficient for 5-8 matrix rows.
        """
        from prompts.executive_summary import _format_chunks

        context = _format_chunks(chunks)
        web_block = f"\n{web_context}\n" if web_context else ""
        user_prompt = f"""You are analyzing the following sustainability and environmental claims documents:

DOCUMENT CONTEXT:
{context}
{web_block}
{COMPARISON_MATRIX_PROMPT}"""

        # FAST model — comparison is structured output, doesn't need deep reasoning
        # Temperature 0.0 for consistency
        raw = await self.llm_service.complete(
            system_prompt, user_prompt, max_tokens=1000, temperature=0.0, tier="fast"
        )
        logger.info(f"[matrix] raw LLM response: {len(raw)} chars, first 300: {raw[:300]!r}")
        raw = _strip_json_fences(raw)

        # Robust JSON extraction — handle common LLM formatting issues
        data = None
        parse_attempts = [raw]
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            parse_attempts.append(raw[brace_start: brace_end + 1])

        for attempt in parse_attempts:
            try:
                data = json.loads(attempt)
                break
            except (json.JSONDecodeError, ValueError):
                continue

        # Last resort: fix common malformed JSON from smaller models
        if data is None:
            import re

            cleaned = raw[brace_start: brace_end + 1] if brace_start != -1 else raw
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            cleaned = cleaned.replace("'", '"')
            try:
                data = json.loads(cleaned)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Comparison matrix parse failed after all attempts: {e}"
                )
                return []

        matrix_data = (
            data.get("comparisonMatrix", []) if isinstance(data, dict) else []
        )
        rows = []
        for item in matrix_data:
            try:
                rows.append(ComparisonRow(**item))
            except Exception as e:
                logger.warning(f"Skipping malformed matrix row: {e}")
        return rows

    async def _generate_recommendation(
        self,
        system_prompt: str,
        chunks: list[Chunk],
        web_context: str = "",
    ) -> Recommendation:
        """
        Generate sustainability accountability recommendation.
        Uses PREMIUM model (deepseek-v4-pro) — requires strategic reasoning.
        max_tokens=800 is sufficient for a recommendation with 3-5 next steps.
        """
        user_prompt = build_recommendation_prompt(chunks, web_context=web_context)
        raw = await self.llm_service.complete(
            system_prompt, user_prompt, max_tokens=800, tier="quality"
        )
        raw = _strip_json_fences(raw)

        try:
            data = json.loads(raw)
            return Recommendation(**data)
        except Exception as e:
            logger.warning(f"Recommendation parse failed: {e}, using fallback")
            return Recommendation(
                title="Analysis Complete",
                summary="Please review the risks and comparison matrix for details.",
                nextSteps=["Review identified risks", "Compare claims vs. data"],
                confidence=0.5,
            )
