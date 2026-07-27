def build_quick_scan_prompt(claim: str) -> str:
    """
    Build a prompt for the Quick Scan feature — single-claim instant verdict
    without any document context. Returns a mini-verdict JSON.
    """
    return f"""You are a sustainability claims analyst. A user has shown you a single marketing/sustainability claim without any supporting document. Assess it on its own merits.

CLAIM: "{claim}"

Evaluate:
1. Is this claim independently verifiable, or is it inherently vague ("eco-friendly", "green", "natural")?
2. Does it reference a specific standard, certification, or measurable target?
3. Is this the kind of claim that regulators (e.g., ACCC, FTC Green Guides, EU Green Claims Directive) have flagged as commonly misleading?

Return ONLY valid JSON:
{{
  "verdict": "<1-2 sentence assessment of this claim's credibility — what's suspicious, what's missing, or why it might be legitimate.>",
  "whatToLookFor": ["<specific thing to verify>", "<specific thing to verify>", "<specific thing to verify>"],
  "confidence": "<LOW|MEDIUM|HIGH — how confident you are in this assessment>"
}}"""
