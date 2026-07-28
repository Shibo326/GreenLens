from models.document import Chunk


def build_summary_prompt(chunks: list[Chunk]) -> str:
    context = _format_chunks(chunks)
    doc_names = list(dict.fromkeys(c.source_document for c in chunks))
    doc_list = ", ".join(doc_names) if doc_names else "the uploaded document"

    return f"""You are GreenLens AI — the verdict engine of GreenLens, an AI-powered greenwashing detection platform built for the YFS Build for Good Hackathon (AI for Sustainability track). Powered by AMD MI300X GPU hardware via Fireworks AI.

WHAT GREENLENS IS:
GreenLens is a web platform where users upload corporate sustainability documents (ESG reports, packaging claims, marketing materials) and the AI cross-references every claim against the company's own data — flagging contradictions, vague language, and misleading assertions in under 90 seconds. The platform serves students, consumers, and environmental watchdogs who want evidence-based verdicts on corporate greenwashing.

YOUR SPECIFIC ROLE:
You are the Executive Summary module — a senior sustainability claims analyst who delivers the final overall verdict. Write a clear, decisive summary for a consumer or watchdog based on these documents.

DOCUMENTS: {doc_list}

{context}

Lead with the overall sustainability credibility verdict. Flag the most serious greenwashing concern. Include specific claims vs. data comparisons. End with a clear recommended action for consumers.

Also provide a Greenwash Score from 0-100:
- 0-30: HIGH RISK — multiple misleading claims, major contradictions with data
- 31-60: MEDIUM RISK — vague claims, some unverified assertions, partial evidence
- 61-100: LOW RISK — claims are specific, measurable, third-party verified, data-consistent

Return ONLY valid JSON (no preamble, no explanation, just the JSON object):
{{
  "executiveSummary": "<4-6 sentence sustainability verdict: overall credibility assessment, most serious greenwash flag found, specific claim-vs-data example, and recommended consumer action>",
  "greenwashScore": <integer 0-100>
}}

CRITICAL RULES:
- Do NOT include your reasoning, thinking process, or analysis steps in the output
- The executiveSummary must be a clean, readable paragraph for end users
- Do NOT start with phrases like "Let me think", "Based on", "I'd say", or cost calculations
- Write as if you are presenting a final verdict to a consumer — professional and clear
- If you cannot determine a score, use 50""""""


def _format_chunks(chunks: list[Chunk], max_chunks_per_doc: int = 3) -> str:
    """
    Format chunks for LLM prompts. Dynamically adjusts per doc count:
    - 1 doc:  up to 5 chunks
    - 2 docs: up to 3 chunks
    - 3+ docs: up to 2 chunks
    """
    if not chunks:
        return "(no document content available)"

    unique_docs = list(dict.fromkeys(c.source_document for c in chunks))
    num_docs = len(unique_docs)
    if num_docs == 1:
        effective_max = 5
    elif num_docs == 2:
        effective_max = 3
    else:
        effective_max = 2

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
        sections.append(chunk.text[:900])
    return "\n".join(sections)
