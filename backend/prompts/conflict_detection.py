from models.document import Chunk


def build_conflict_prompt(
    doc_a_chunks: list[Chunk],
    doc_b_chunks: list[Chunk],
    doc_a_name: str,
    doc_b_name: str,
) -> str:
    def fmt(chunks: list[Chunk]) -> str:
        return "\n".join(c.text[:900] for c in chunks[:8])

    content_a = fmt(doc_a_chunks)
    content_b = fmt(doc_b_chunks)

    return f"""You are GreenLens AI — a forensic sustainability claims analyst who detects contradictions between what companies SAY (marketing, packaging, public claims) and what their own DATA SHOWS (sustainability reports, audit results, emissions data). Your job is to find factual contradictions that reveal greenwashing.

=== DOCUMENT A (CLAIMS): {doc_a_name} ===
{content_a}

=== DOCUMENT B (DATA/EVIDENCE): {doc_b_name} ===
{content_b}

YOUR ANALYTICAL PROCESS:
1. ALIGN: Identify environmental/sustainability topics discussed in BOTH documents
2. COMPARE: For each shared topic, check if the marketing claim is supported by the reported data
3. VERIFY: Confirm that differences are genuine contradictions (not just different levels of detail)
4. ASSESS: For each real contradiction, determine how misleading it is to consumers
5. PRESCRIBE: Recommend exactly what accountability action should follow

WHAT COUNTS AS A CONTRADICTION:
✓ Claim says "carbon neutral" but report shows only partial scope offsetting
✓ Packaging says "100% recycled" but data shows only one component is recycled
✓ Marketing says "zero waste to landfill" but report shows exceptions/exclusions
✓ Claim cites a certification that doesn't cover the product/scope being implied
✓ Marketing implies current achievement but report reveals it's a future target
✓ Headline metric contradicts the detailed breakdown in the same report

WHAT IS NOT A CONTRADICTION:
✗ Different levels of detail about different sustainability topics
✗ Information in one document that's simply absent from the other (that's an evidence gap, not a contradiction)
✗ Stylistic or formatting differences
✗ Complementary information that doesn't contradict

FOR EACH CONTRADICTION — THINK DEEPER:
- How would a reasonable consumer interpret the claim vs. what the data actually shows?
- Does this match patterns of known greenwashing tactics (hidden trade-off, vagueness, irrelevance)?
- Has a similar contradiction resulted in regulatory action elsewhere?
- How urgent is this — are consumers being actively misled right now?

SEVERITY:
- HIGH: Claim directly contradicts reported data — consumers are being actively misled. This is the type of discrepancy regulators fine companies for.
- MEDIUM: Claim is technically defensible but the framing creates a materially misleading impression when compared to the full data. Requires clarification.
- LOW: Minor inconsistency or scope mismatch that could confuse attentive readers but is unlikely to constitute deceptive marketing on its own.

If no genuine contradictions exist between these two documents, return an empty conflicts array. Do NOT invent contradictions to appear thorough.

Return ONLY valid JSON:
{{
  "conflicts": [
    {{
      "id": "c1",
      "type": "<specific contradiction type: 'Scope Mismatch', 'Unsubstantiated Claim', 'Metric Contradiction', 'Timeline Misrepresentation', 'Certification Overreach', etc. — be descriptive>",
      "severity": "HIGH",
      "documentA": {{
        "name": "{doc_a_name}",
        "excerpt": "<exact verbatim quote from Document A showing the marketing claim — max 150 chars>"
      }},
      "documentB": {{
        "name": "{doc_b_name}",
        "excerpt": "<exact verbatim quote from Document B showing the contradicting data — max 150 chars>"
      }},
      "explanation": "<WHY these statements contradict each other + consumer impact. Include: the specific discrepancy, what a consumer would reasonably believe vs. what's actually true, and regulatory precedent if applicable.>",
      "recommendedAction": "<Specific accountability step: what question to ask the company, what disclosure to demand, what verification to seek, and what regulatory body to report to if unresolved.>"
    }}
  ]
}}"""
