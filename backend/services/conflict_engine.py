import json
import logging

from models.document import Chunk
from models.response import Conflict
from prompts.system_prompt import get_system_prompt
from services.llm_service import LLMService, _strip_json_fences

logger = logging.getLogger(__name__)


class ConflictEngine:
    """
    Detects factual contradictions between documents in a session.
    Uses a single consolidated LLM call to analyze ALL documents at once,
    instead of expensive pairwise comparisons (N*(N-1)/2 calls -> 1 call).

    Uses the FAST model (gpt-oss-120b) — conflict detection is a structured
    extraction task that doesn't require deep reasoning.
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def detect(
        self,
        chunks: list[Chunk],
        document_names: list[str],
    ) -> list[Conflict]:
        """
        Analyze ALL documents in a single LLM call for conflicts.

        Args:
            chunks: All chunks in the session
            document_names: List of document filenames to compare

        Returns:
            List of detected Conflict objects
        """
        if len(document_names) < 2:
            logger.debug("Fewer than 2 documents — skipping conflict detection")
            return []

        # Group chunks by source document
        doc_chunks: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            doc = chunk.source_document
            if doc not in doc_chunks:
                doc_chunks[doc] = []
            doc_chunks[doc].append(chunk)

        # Build a single prompt with ALL document excerpts
        prompt = self._build_consolidated_prompt(doc_chunks, document_names)
        system_prompt = get_system_prompt(document_names)

        logger.info(
            f"Running consolidated conflict detection across {len(document_names)} documents (1 LLM call, fast model)"
        )

        # Conflict detection uses QUALITY model (deepseek-v4-flash):
        # - requires reasoning to compare documents and identify contradictions
        # - 2000 tokens: enough for up to 6 well-formed conflicts with detailed explanations
        # - Temperature 0.0 for maximum consistency
        try:
            raw = await self.llm_service.complete(
                system_prompt, prompt, max_tokens=2000, temperature=0.0, fast=False
            )
            logger.info(f"[conflicts] raw LLM response: {len(raw)} chars, first 300: {raw[:300]!r}")
            raw = _strip_json_fences(raw)
            logger.info(f"[conflicts] after strip, first 200: {raw[:200]!r}")
            conflicts = self._parse_conflicts(raw)

            # CONSISTENCY FIX: If 0 conflicts found for multi-doc session, retry once
            # Documents with different terms/prices almost always have conflicts
            if not conflicts and len(document_names) >= 2:
                logger.warning("[conflicts] Zero conflicts returned for multi-doc session — retrying with stricter prompt")
                retry_prompt = (
                    prompt
                    + "\n\nIMPORTANT: You returned zero conflicts, but these are separate documents about the SAME transaction/relationship. "
                    "Look again for: (1) price differences between documents, (2) different payment terms, "
                    "(3) quantities or specifications that don't match, (4) any clause in one document that contradicts another. "
                    "If one document says Net 60 and another says Net 30, that IS a conflict. "
                    "If amounts don't match, that IS a conflict. Return at least the most obvious conflicts."
                )
                try:
                    raw2 = await self.llm_service.complete(
                        system_prompt, retry_prompt, max_tokens=2000, temperature=0.0, fast=False
                    )
                    raw2 = _strip_json_fences(raw2)
                    conflicts2 = self._parse_conflicts(raw2)
                    if conflicts2:
                        conflicts = conflicts2
                        logger.info(f"[conflicts] Retry succeeded — got {len(conflicts)} conflicts")
                except Exception as retry_err:
                    logger.warning(f"[conflicts] Retry failed: {retry_err}")

            logger.info(
                f"Found {len(conflicts)} conflict(s) across {len(document_names)} documents"
            )
            return conflicts
        except Exception as e:
            logger.warning(f"Consolidated conflict detection failed: {e}")
            return []

    def _build_consolidated_prompt(
        self,
        doc_chunks: dict[str, list[Chunk]],
        document_names: list[str],
    ) -> str:
        """Build a single prompt containing all document excerpts for conflict analysis."""
        num_docs = len(doc_chunks)
        # Dynamic chunk allocation per document count — balanced for speed vs coverage
        if num_docs == 1:
            max_per_doc, max_chars = 6, 800
        elif num_docs == 2:
            max_per_doc, max_chars = 5, 700
        elif num_docs == 3:
            max_per_doc, max_chars = 4, 650
        else:
            max_per_doc, max_chars = max(2, 10 // num_docs), 600

        sections = []
        for i, doc_name in enumerate(document_names, 1):
            chunks = doc_chunks.get(doc_name, [])
            if not chunks:
                continue
            content = "\n".join(c.text[:max_chars] for c in chunks[:max_per_doc])
            sections.append(f"=== DOCUMENT {i}: {doc_name} ===\n{content}")

        all_docs_content = "\n\n".join(sections)
        doc_list = ", ".join(document_names)

        return f"""You are GreenLens AI — a forensic document analyst with the precision of an auditor and the strategic awareness of a deal advisor. Analyze ALL of the following documents and identify factual conflicts BETWEEN them that could create legal, financial, or operational exposure.

DOCUMENTS TO COMPARE: {doc_list}

{all_docs_content}

YOUR ANALYTICAL PROCESS:
1. ALIGN: For each pair of documents, identify subjects, terms, dates, figures, and obligations discussed in BOTH
2. COMPARE: Check if statements about the SAME subject are compatible or contradictory
3. VERIFY: Confirm contradictions are genuine (not just different levels of detail about different topics)
4. QUANTIFY: For each real conflict, estimate the financial or legal exposure
5. PRIORITIZE: Rank by impact — which conflicts need immediate resolution?

WHAT COUNTS AS A CONFLICT:
- Price/value discrepancies (e.g., contract says $100/unit, invoice charges $107)
- Conflicting dates or deadlines (delivery by March 15 in one, April 1 in another)
- Contradictory terms (Net 30 vs. Net 60 for the same relationship)
- Mismatched quantities or specifications
- Incompatible obligations (Party A must do X in one document, opposite in another)
- Inconsistent party identification or role definitions

NOT A CONFLICT:
- Different levels of detail about DIFFERENT subjects
- Information in one document simply absent from another (that's a gap, not a conflict)
- Stylistic or formatting differences
- Complementary information that doesn't contradict

SEVERITY:
- HIGH: Direct financial impact (active overcharging), legal liability, or approaching deadline.
- MEDIUM: Material inconsistency that will cause problems if not resolved before next milestone.
- LOW: Minor discrepancy — worth documenting but limited immediate impact.

If no genuine conflicts exist, return an empty array. Do NOT invent conflicts to appear thorough.

Return ONLY valid JSON:
{{
  "conflicts": [
    {{
      "id": "c1",
      "type": "<specific conflict type: 'Unit Price Discrepancy ($7/unit delta)', 'Payment Terms Contradiction (Net 30 vs Net 60)', etc.>",
      "severity": "HIGH",
      "documentA": {{
        "name": "<document name>",
        "excerpt": "<exact verbatim quote showing the conflicting claim — max 150 chars>"
      }},
      "documentB": {{
        "name": "<other document name>",
        "excerpt": "<exact verbatim quote showing the contradicting claim — max 150 chars>"
      }},
      "explanation": "<WHY incompatible + financial/legal impact + which version is likely authoritative + what happens if unresolved>",
      "recommendedAction": "<specific resolution: who does what, using which document as truth, by when, and how to prevent recurrence>"
    }}
  ]
}}"""

    def _parse_conflicts(self, raw: str) -> list[Conflict]:
        """Parse the LLM response into Conflict objects with aggressive JSON extraction."""
        import re

        # Aggressive brace extraction — same pattern as chat.py
        brace_start = raw.find("{")
        brace_end = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start:brace_end + 1]
        raw = raw.strip()

        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            # Try cleaning trailing commas
            cleaned = re.sub(r',\s*([}\]])', r'\1', raw)
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse conflict JSON: {e}. Raw first 500: {raw[:500]!r}")
                return []

        # Handle both formats: {"conflicts": [...]} or bare array [...]
        if isinstance(data, dict):
            data = data.get("conflicts", [])

        if not isinstance(data, list):
            logger.warning(
                f"Conflict response is not a list or wrapped object: {type(data)}"
            )
            return []

        conflicts = []
        for i, item in enumerate(data):
            try:
                item["id"] = f"c{i + 1}"
                conflict = Conflict(**item)
                conflicts.append(conflict)
            except Exception as e:
                logger.warning(f"Skipping malformed conflict item {i}: {e}")
                continue

        return conflicts
