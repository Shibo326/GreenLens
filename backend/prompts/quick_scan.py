def build_quick_scan_prompt(claim: str, web_context: str = "") -> str:
    """
    Build a prompt for the Quick Scan feature — single-claim instant verdict
    without any document context. Returns a mini-verdict JSON.

    Optionally includes web research context for real-time cross-referencing.
    """
    web_block = ""
    if web_context:
        web_block = f"""

{web_context}

Use the web research above to enrich your verdict — cite specific findings if relevant. Mention if online sources corroborate or contradict this claim.
"""

    return f"""You are a sustainability claims analyst. A user has shown you a single marketing/sustainability claim without any supporting document. Assess it on its own merits.

CLAIM: "{claim}"
{web_block}
Evaluate:
1. Is this claim independently verifiable, or is it inherently vague ("eco-friendly", "green", "natural")?
2. Does it reference a specific standard, certification, or measurable target?
3. Is this the kind of claim that regulators (e.g., ACCC, FTC Green Guides, EU Green Claims Directive) have flagged as commonly misleading?
4. Does real-time web research (if available) reveal any relevant context about this company or claim type?

Return ONLY valid JSON:
{{
  "verdict": "<1-2 sentence assessment of this claim's credibility — what's suspicious, what's missing, or why it might be legitimate. If web research found relevant info, mention it briefly.>",
  "whatToLookFor": ["<specific thing to verify>", "<specific thing to verify>", "<specific thing to verify>"],
  "confidence": "<LOW|MEDIUM|HIGH — how confident you are in this assessment>"
}}"""
