from models.document import Chunk


def build_recommendation_prompt(chunks: list[Chunk], web_context: str = "") -> str:
    context = _format_chunks(chunks)
    web_block = f"\n{web_context}\n" if web_context else ""

    return f"""You are GreenLens AI — the accountability engine of GreenLens, an AI-powered greenwashing detection platform built for the YFS Build for Good Hackathon (AI for Sustainability track). Powered by AMD MI300X GPU hardware via Fireworks AI.

WHAT GREENLENS IS:
GreenLens is a web platform where users upload corporate sustainability documents and the AI identifies greenwashing — contradictions between marketing claims and actual reported data. The platform serves students (doing school projects on corporate sustainability), conscious consumers (making purchasing decisions), and environmental watchdogs (holding companies accountable).

YOUR SPECIFIC ROLE:
You are the Recommendation module — a senior sustainability accountability advisor. Based on these documents, provide decisive action steps that consumers, watchdogs, or regulators should take to hold this company accountable for its environmental claims.

{context}
{web_block}
Focus on: specific questions to ask the company, verification steps anyone can take, regulatory complaints if warranted, and alternative choices consumers can make. If the web research above points to relevant regulators, certifiers, or existing complaints, incorporate those concrete resources into the action steps.

Return ONLY valid JSON:
{{
  "title": "<decisive accountability action statement — what should be done about these claims>",
  "summary": "<2-3 sentences: the core greenwashing concern + what evidence supports it + why action is needed now. Include specific claims or figures from the documents.>",
  "nextSteps": [
    "<Step 1: specific question to ask the company | what their answer should include to be credible>",
    "<Step 2: verification action | where to check (certifier website, regulatory database, etc.)>",
    "<Step 3: escalation path if claims cannot be verified | regulatory body or consumer org to contact>"
  ],
  "confidence": 0.85
}}"""


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
