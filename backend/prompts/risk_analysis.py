import re
from models.document import Chunk


def build_risk_prompt(chunks: list[Chunk]) -> str:
    context = _format_chunks_for_risk(chunks)

    return f"""You are a senior sustainability claims analyst specializing in greenwashing detection. Analyze the documents below and identify ALL greenwash flags — claims that are misleading, vague, or unverified.

CRITICAL INSTRUCTION: For sustainability claims, marketing materials, and corporate environmental communications, there are ALWAYS flags to identify. If you find contradictions with data, unmeasurable language, or uncertified assertions, you MUST report them. Returning zero flags for documents with environmental claims is INCORRECT.

DOCUMENTS:
{context}

GREENWASH FLAG CHECKLIST — check every one:
1. MISLEADING CLAIMS (HIGH): Claims that directly contradict available data, overstate environmental benefit, misrepresent scope/coverage, or use false/expired certifications
2. VAGUE CLAIMS (MEDIUM): Unmeasurable language ("eco-friendly", "green", "natural", "sustainable"), claims without specific metrics or timelines, undefined scope boundaries, ambiguous qualifiers
3. UNVERIFIED CLAIMS (LOW): Assertions without third-party certification, self-declared environmental benefits without methodology disclosure, claims citing internal audits only, missing standard frameworks (GRI, SASB, ISO 14001)
4. HIDDEN TRADE-OFFS: Highlighting one green attribute while ignoring larger environmental impact (e.g., "recyclable packaging" on a high-emissions product)
5. IRRELEVANCE: Technically true claims that are meaningless (e.g., "CFC-free" when CFCs are banned anyway)

Return ONLY valid JSON (start your response with the opening brace, no preamble, no thinking tags):
{{
  "risks": [
    {{
      "id": "r1",
      "level": "HIGH",
      "description": "<specific greenwash flag with document evidence: what the claim says, why it's problematic, what a consumer would wrongly believe, and what verification is missing>",
      "sourceDocument": "<exact filename>",
      "category": "<Misleading | Vague | Unverified | Hidden Trade-off | Irrelevance | Scope Manipulation>"
    }}
  ]
}}

Severity guide:
- HIGH: Claim directly contradicts data or makes a demonstrably false/deceptive assertion (MISLEADING) — regulators would likely take action
- MEDIUM: Claim uses vague, unmeasurable, or unqualified language that creates a misleading impression (VAGUE) — needs specific metrics/qualifiers to be legitimate
- LOW: Claim may be accurate but has no third-party verification or recognized certification (UNVERIFIED) — could be true but consumers can't confirm it

You MUST identify at least 3 greenwash flags for any document set with environmental/sustainability claims. Look for: (1) claims without supporting data, (2) vague/unmeasurable language, (3) scope mismatches between headline claims and fine print.

Return ONLY the JSON object starting with {{. No explanation, no markdown, no thinking."""


# Regex patterns that signal greenwash-relevant content
_RISK_SIGNALS = re.compile(
    r'\bcarbon\b|\bnet.zero\b|\bneutral\b|\bsustain|\brecycl|\bbiodegrad|\brenewable\b'
    r'|\beco.friendly\b|\bgreen\b|\borganic\b|\bnatural\b|\bclean\b|\boffset'
    r'|\bemission|\bscope\s*[123]\b|\bcertif|\biso\s*14|\bGRI\b|\bSASB\b'
    r'|\bplastic.free\b|\bzero.waste\b|\bcompost|\bplant.based\b|\bfair.trade\b'
    r'|\bresponsib|\bethical\b|\bcruelty.free\b|\bvegan\b|\benergy.efficien',
    re.IGNORECASE,
)


def _format_chunks_for_risk(chunks: list[Chunk], max_chunks_per_doc: int = 8) -> str:
    """
    Format chunks for greenwash flag analysis. Dynamically adjusts chunks-per-doc based on
    total document count to balance speed vs coverage:
    - 1 doc:  up to 12 chunks at 1200 chars — full coverage
    - 2 docs: up to 8 chunks at 1000 chars — balanced
    - 3 docs: up to 6 chunks at 900 chars — split evenly
    - 4+ docs: up to 4 chunks at 800 chars — prioritize high-signal chunks
    """
    if not chunks:
        return "(no document content available)"

    from collections import defaultdict
    doc_chunks: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        doc_chunks[chunk.source_document].append(chunk)

    num_docs = len(doc_chunks)

    if num_docs == 1:
        max_per_doc = 10
        max_chars = 1200
    elif num_docs == 2:
        max_per_doc = 7
        max_chars = 1000
    elif num_docs == 3:
        max_per_doc = 5
        max_chars = 900
    else:
        max_per_doc = max(3, 10 // num_docs)
        max_chars = 800

    sections = []
    for doc_name, doc_chunk_list in doc_chunks.items():
        # Score each chunk by greenwash-signal density
        scored = sorted(
            doc_chunk_list,
            key=lambda c: len(_RISK_SIGNALS.findall(c.text)),
            reverse=True,
        )
        selected = scored[:max_per_doc]
        # Re-sort by original position for readability
        selected.sort(key=lambda c: doc_chunk_list.index(c))

        sections.append(f"\n=== {doc_name} ===")
        for chunk in selected:
            sections.append(chunk.text[:max_chars])

    return "\n".join(sections)


def _format_chunks(chunks: list[Chunk], max_chunks_per_doc: int = 3) -> str:
    """
    Format chunks for LLM prompts. Dynamically adjusts per doc count:
    - 1 doc:  up to 5 chunks — more context for single-doc analysis
    - 2 docs: up to 3 chunks — balanced
    - 3+ docs: up to 2 chunks — keep input tight
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
