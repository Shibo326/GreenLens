"""
Property-based and unit tests for HybridRetrievalService.

Covers design properties:
  * Property 4  - cosine distance filtering
  * Property 16 - hybrid retrieval broadens recall
  * Property 17 - named entity boost ranking
  * Property 18 - document type filtering correctness
  * Property 19 - diversity selection outperforms naive top-k

All tests run fully offline: fake VectorStore / EmbeddingService are injected and
the re-ranker falls back to the deterministic pure-Python lexical scorer, so no
model is downloaded and no API key is required.
"""

from __future__ import annotations

import os
import sys

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.document import Chunk  # noqa: E402
from models.retrieval import RankedChunk, ScoredChunk  # noqa: E402
from services.hybrid_retrieval import HybridRetrievalService  # noqa: E402

DOC_TYPES = ["pdf", "image", "document"]


# ---------------------------------------------------------------------------
# Fakes (no models, no Chroma, no network)
# ---------------------------------------------------------------------------


class FakeEmbeddingService:
    """Deterministic stand-in for EmbeddingService.embed()."""

    def __init__(self):
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text) % 7), 0.5, 0.25]


class FakeVectorStore:
    """
    Stand-in for VectorStore.

    `semantic_order` lists chunk ids in semantic-relevance order; `distances`
    maps chunk id -> cosine distance returned by the semantic search.
    """

    def __init__(
        self,
        chunks: list[Chunk],
        semantic_order: list[str] | None = None,
        distances: dict[str, float] | None = None,
    ):
        self.chunks = chunks
        self.semantic_order = semantic_order or [c.id for c in chunks]
        self.distances = distances or {c.id: 0.2 for c in chunks}

    def query_top_k(self, session_id: str, embedding: list[float], k: int = 5) -> list[Chunk]:
        by_id = {c.id: c for c in self.chunks}
        out: list[Chunk] = []
        for chunk_id in self.semantic_order[:k]:
            chunk = by_id.get(chunk_id)
            if chunk is None:
                continue
            out.append(chunk.model_copy(update={"distance": self.distances.get(chunk_id, 0.2)}))
        return out

    def get_all_chunks(self, session_id: str) -> list[Chunk]:
        return [c.model_copy(update={"distance": None}) for c in self.chunks]


def make_chunk(
    chunk_id: str,
    text: str,
    source: str = "doc_a.pdf",
    doc_type: str = "pdf",
    index: int = 0,
    distance: float | None = None,
) -> Chunk:
    return Chunk(
        id=chunk_id,
        text=text,
        embedding=[0.1, 0.2, 0.3],
        source_document=source,
        document_type=doc_type,
        chunk_index=index,
        distance=distance,
    )


def make_ranked(
    chunk_id: str, source: str, score: float, words: int = 30, doc_type: str = "pdf"
) -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk_id,
        text=" ".join(["word"] * words),
        source_document=source,
        document_type=doc_type,
        combined_score=score,
    )


def naive_top_k(chunks: list[RankedChunk], budget_tokens: int) -> list[RankedChunk]:
    """Baseline: greedily take the highest scoring chunks that fit the budget."""
    ordered = sorted(chunks, key=lambda c: (-c.combined_score, c.chunk_id))
    selected: list[RankedChunk] = []
    used = 0
    for chunk in ordered:
        cost = HybridRetrievalService.estimate_tokens(chunk.text)
        if used + cost <= budget_tokens:
            selected.append(chunk)
            used += cost
    if not selected and ordered:
        selected = [ordered[0]]
    return selected


def unique_sources(chunks: list[RankedChunk]) -> set[str]:
    return {c.source_document for c in chunks}


@pytest.fixture
def service() -> HybridRetrievalService:
    """Service with fakes injected — reranker left as the offline fallback."""
    return HybridRetrievalService(
        vector_store=FakeVectorStore([]),
        embedding_service=FakeEmbeddingService(),
    )


# ---------------------------------------------------------------------------
# Property 4: Cosine distance filtering
# ---------------------------------------------------------------------------


# Feature: ai-advanced-training, Property 4: cosine distance filtering
@given(
    distances=st.lists(
        st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=25,
    )
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_property_4_distance_filtering(distances):
    """
    Property 4: distance filtering excludes every chunk with distance > 0.7,
    includes every chunk with distance <= 0.7, and the output is always a
    subset of the input.
    """
    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]), embedding_service=FakeEmbeddingService()
    )
    chunks = [
        make_chunk(f"c{i}", f"chunk text {i}", distance=d)
        for i, d in enumerate(distances)
    ]

    kept = svc.filter_by_distance(chunks)
    kept_ids = [c.id for c in kept]
    input_ids = [c.id for c in chunks]

    # Subset
    assert set(kept_ids).issubset(set(input_ids))
    # Exclusion + inclusion are exact
    for chunk in chunks:
        if chunk.distance is not None and chunk.distance > 0.7:
            assert chunk.id not in kept_ids, f"distance {chunk.distance} should be excluded"
        else:
            assert chunk.id in kept_ids, f"distance {chunk.distance} should be included"


def test_property_4_boundary_and_missing_distance(service):
    """Distance exactly 0.7 is kept; None (BM25-only candidate) is kept."""
    chunks = [
        make_chunk("keep_boundary", "text", distance=0.7),
        make_chunk("drop", "text", distance=0.70001),
        make_chunk("keep_none", "text", distance=None),
    ]
    kept = {c.id for c in service.filter_by_distance(chunks)}
    assert kept == {"keep_boundary", "keep_none"}


@pytest.mark.asyncio
async def test_retrieve_applies_distance_filter():
    """Semantic hits beyond the 0.7 cut-off never reach the result set."""
    chunks = [
        make_chunk("near", "carbon neutral pledge audited by a third party", "a.pdf"),
        make_chunk("far", "unrelated quarterly office supplies budget", "b.pdf", index=1),
    ]
    store = FakeVectorStore(
        chunks,
        semantic_order=["near", "far"],
        distances={"near": 0.15, "far": 0.95},
    )
    svc = HybridRetrievalService(vector_store=store, embedding_service=FakeEmbeddingService())

    results = await svc.retrieve("carbon neutral pledge", "s1", k=5, max_tokens=100000)
    ids = {r.chunk_id for r in results}
    assert "near" in ids
    # "far" may only appear via BM25 keyword overlap; with a disjoint vocabulary
    # it must not appear at all.
    assert "far" not in ids


# ---------------------------------------------------------------------------
# Property 16: Hybrid retrieval broadens recall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_property_16_hybrid_superset_of_both_methods():
    """
    Property 16: the hybrid result set does not exclude anything that appeared
    in the top-k of either semantic search or BM25 alone.
    """
    corpus = [
        make_chunk("c1", "Acme Corp claims carbon neutral operations by 2030", "acme.pdf", index=0),
        make_chunk("c2", "The supplier reports recycled packaging content", "supp.pdf", "document", 1),
        make_chunk("c3", "carbon offsets purchased from an unverified registry", "acme.pdf", index=2),
        make_chunk("c4", "employee wellness programme and office catering", "hr.pdf", index=3),
        make_chunk("c5", "neutral tone marketing language about green energy", "mkt.pdf", index=4),
        make_chunk("c6", "third party audit of emissions data completed", "audit.pdf", index=5),
    ]
    # Semantic order deliberately favours chunks with little keyword overlap so
    # the two methods disagree.
    store = FakeVectorStore(
        corpus,
        semantic_order=["c4", "c6", "c2", "c1", "c3", "c5"],
        distances={c.id: 0.1 + 0.05 * i for i, c in enumerate(corpus)},
    )
    svc = HybridRetrievalService(vector_store=store, embedding_service=FakeEmbeddingService())

    query = "carbon neutral claims"
    k = 3

    semantic_only = svc.filter_by_distance(store.query_top_k("s1", [0.0], k=k))
    bm25_only = svc.bm25_search(query, store.get_all_chunks("s1"), k=k)
    assert semantic_only, "fixture should produce semantic hits"
    assert bm25_only, "fixture should produce BM25 hits"

    results = await svc.retrieve(query, "s1", k=k, max_tokens=100000)
    result_ids = {r.chunk_id for r in results}

    for chunk in semantic_only:
        assert chunk.id in result_ids, f"semantic hit {chunk.id} was dropped"
    for scored in bm25_only:
        assert scored.chunk_id in result_ids, f"BM25 hit {scored.chunk_id} was dropped"

    # And the hybrid set is genuinely broader than either method alone.
    assert len(result_ids) >= max(len(semantic_only), len(bm25_only))


def test_bm25_search_ranks_keyword_matches_first(service):
    """BM25 puts the chunk with the query terms on top and skips zero-overlap chunks."""
    corpus = [
        make_chunk("hit", "recycled aluminium packaging reduces emissions"),
        make_chunk("miss", "quarterly staff parking allocation policy", index=1),
        make_chunk("filler", "company sustainability reporting guidelines overview", index=2),
    ]
    scored = service.bm25_search("recycled aluminium packaging", corpus, k=5)
    assert scored
    assert isinstance(scored[0], ScoredChunk)
    assert scored[0].chunk_id == "hit"
    assert scored[0].method == "bm25"
    # Only chunks with actual query-term overlap are returned
    assert all(s.chunk_id == "hit" for s in scored)
    assert scored[0].score > 0


def test_bm25_search_edge_cases(service):
    """Empty query or empty corpus yields no results, and k bounds the output."""
    corpus = [make_chunk(f"c{i}", f"green claim number {i} about emissions", index=i) for i in range(6)]
    assert service.bm25_search("", corpus) == []
    assert service.bm25_search("green", []) == []
    assert len(service.bm25_search("green claim emissions", corpus, k=2)) == 2


# ---------------------------------------------------------------------------
# Property 17: Named entity boost ranking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_property_17_named_entity_boost_ranking():
    """
    Property 17: for a query containing named entity E, chunks containing the
    exact string E score higher than otherwise-equivalent chunks lacking E.
    """
    shared = "reported a reduction in operational emissions during the period"
    with_entity = make_chunk("with", f"Northwind Energy {shared}", "a.pdf", index=0)
    without_entity = make_chunk("without", f"the operator {shared}", "b.pdf", index=1)

    store = FakeVectorStore(
        [with_entity, without_entity],
        semantic_order=["with", "without"],
        # Identical distances => identical semantic contribution.
        distances={"with": 0.3, "without": 0.3},
    )
    svc = HybridRetrievalService(vector_store=store, embedding_service=FakeEmbeddingService())

    results = await svc.retrieve("Northwind Energy emissions reduction", "s1", k=5, max_tokens=100000)
    scores = {r.chunk_id: r.combined_score for r in results}

    assert "with" in scores and "without" in scores
    assert scores["with"] > scores["without"]


def test_entity_extraction_and_boost_are_deterministic(service):
    """Entity extraction finds capitalised spans; the boost is exact-match only."""
    entities = service.extract_entities("Did Northwind Energy mislead the FTC about carbon?")
    assert "Northwind Energy" in entities
    assert "FTC" in entities

    assert service.entity_boost("Northwind Energy pledged net zero", entities) > 0
    assert service.entity_boost("an unnamed operator pledged net zero", entities) == 0.0
    # Case-sensitive exact string matching.
    assert service.entity_boost("northwind energy pledged net zero", ["Northwind Energy"]) == 0.0


# Feature: ai-advanced-training, Property 17: named entity boost ranking
@given(
    entity=st.sampled_from(["Northwind Energy", "Acme Corp", "FTC", "Shell", "Nestle"]),
    filler=st.text(
        alphabet=st.characters(whitelist_categories=("Ll",)), min_size=3, max_size=12
    ),
)
@settings(max_examples=40, deadline=None)
def test_property_17_boost_monotonic(entity, filler):
    """A chunk containing E always scores at least as high a boost as one without."""
    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]), embedding_service=FakeEmbeddingService()
    )
    entities = svc.extract_entities(f"what did {entity} claim about emissions")
    assume(entity in entities)

    boosted = svc.entity_boost(f"{filler} {entity} {filler}", entities)
    plain = svc.entity_boost(f"{filler} the company {filler}", entities)
    assert boosted > plain


# ---------------------------------------------------------------------------
# Property 18: Document type filtering correctness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("doc_type", DOC_TYPES)
@pytest.mark.asyncio
async def test_property_18_doc_type_filter(doc_type):
    """
    Property 18: when doc_type_filter is set, EVERY chunk in the result has a
    matching document_type — no other type appears.
    """
    corpus = []
    for i, dtype in enumerate(DOC_TYPES * 3):
        corpus.append(
            make_chunk(
                f"c{i}",
                f"green claim about recycled emissions data {i}",
                source=f"doc_{i % 4}.pdf",
                doc_type=dtype,
                index=i,
            )
        )
    store = FakeVectorStore(corpus, distances={c.id: 0.1 for c in corpus})
    svc = HybridRetrievalService(vector_store=store, embedding_service=FakeEmbeddingService())

    results = await svc.retrieve(
        "recycled emissions data", "s1", k=6, max_tokens=100000, doc_type_filter=doc_type
    )

    assert results, "filter should still return the matching-type chunks"
    assert all(r.document_type == doc_type for r in results)
    assert {r.document_type for r in results} == {doc_type}


@pytest.mark.asyncio
async def test_property_18_no_filter_allows_all_types():
    """Without a filter, multiple document types can appear."""
    corpus = [
        make_chunk("p", "recycled emissions data pdf", doc_type="pdf", index=0),
        make_chunk("i", "recycled emissions data image", doc_type="image", index=1, source="b.pdf"),
    ]
    store = FakeVectorStore(corpus, distances={c.id: 0.1 for c in corpus})
    svc = HybridRetrievalService(vector_store=store, embedding_service=FakeEmbeddingService())

    results = await svc.retrieve("recycled emissions data", "s1", k=5, max_tokens=100000)
    assert {r.document_type for r in results} == {"pdf", "image"}


# ---------------------------------------------------------------------------
# Property 19: Diversity selection outperforms naive top-k
# ---------------------------------------------------------------------------


# Feature: ai-advanced-training, Property 19: diversity selection outperforms naive top-k
@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=6,
        max_size=12,
        unique=True,
    ),
    source_picks=st.lists(st.integers(min_value=0, max_value=2), min_size=6, max_size=12),
    budget_chunks=st.integers(min_value=1, max_value=4),
)
@settings(max_examples=60, deadline=None)
def test_property_19_diversity_at_least_as_many_sources(scores, source_picks, budget_chunks):
    """
    Property 19 (part 1): with chunks from 3+ distinct sources and a
    constraining token budget, diversity selection covers at least as many
    unique sources as naive top-k.
    """
    n = min(len(scores), len(source_picks))
    assume(n >= 6)
    scores = scores[:n]
    source_picks = source_picks[:n]
    assume(len(set(source_picks)) >= 3)
    assume(budget_chunks < n)

    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]), embedding_service=FakeEmbeddingService()
    )
    # Uniform chunk size so the budget constrains the *count*, not the shape.
    chunks = [
        make_ranked(f"c{i}", f"doc_{source_picks[i]}.pdf", scores[i], words=30)
        for i in range(n)
    ]
    per_chunk = HybridRetrievalService.estimate_tokens(chunks[0].text)
    budget = per_chunk * budget_chunks

    diverse = svc.select_diverse(chunks, budget_tokens=budget)
    naive = naive_top_k(chunks, budget)

    assert len(diverse) == len(naive), "both strategies fill the same budget"
    assert len(unique_sources(diverse)) >= len(unique_sources(naive))
    # Output is a subset of the input.
    assert {c.chunk_id for c in diverse}.issubset({c.chunk_id for c in chunks})


def test_property_19_strictly_more_sources_when_concentrated(service):
    """
    Property 19 (part 2): when the top scorers are concentrated in one source,
    diversity selection returns strictly more unique sources than naive top-k.
    """
    chunks = [
        make_ranked("a1", "doc_a.pdf", 0.99),
        make_ranked("a2", "doc_a.pdf", 0.98),
        make_ranked("a3", "doc_a.pdf", 0.97),
        make_ranked("b1", "doc_b.pdf", 0.50),
        make_ranked("c1", "doc_c.pdf", 0.40),
    ]
    per_chunk = HybridRetrievalService.estimate_tokens(chunks[0].text)
    budget = per_chunk * 2  # room for exactly two chunks

    diverse = service.select_diverse(chunks, budget_tokens=budget)
    naive = naive_top_k(chunks, budget)

    assert len(naive) == 2 and len(unique_sources(naive)) == 1
    assert len(diverse) == 2
    assert len(unique_sources(diverse)) > len(unique_sources(naive))
    # The single best chunk is still retained.
    assert "a1" in {c.chunk_id for c in diverse}


def test_select_diverse_edge_cases(service):
    """Empty input returns empty; an over-budget best chunk is still returned."""
    assert service.select_diverse([], budget_tokens=100) == []

    single = [make_ranked("big", "doc_a.pdf", 0.9, words=500)]
    result = service.select_diverse(single, budget_tokens=10)
    assert [c.chunk_id for c in result] == ["big"]


def test_select_diverse_respects_token_budget(service):
    """Selected chunks never exceed the token budget when at least one fits."""
    chunks = [make_ranked(f"c{i}", f"doc_{i}.pdf", 1.0 - i * 0.1, words=30) for i in range(6)]
    per_chunk = HybridRetrievalService.estimate_tokens(chunks[0].text)
    budget = per_chunk * 3
    selected = service.select_diverse(chunks, budget_tokens=budget)
    total = sum(HybridRetrievalService.estimate_tokens(c.text) for c in selected)
    assert total <= budget
    assert len(selected) == 3


# ---------------------------------------------------------------------------
# Re-ranking: offline fallback and injected re-ranker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerank_fallback_is_offline_and_deterministic(service):
    """The fallback re-ranker needs no model and gives stable ordering."""
    chunks = [
        make_chunk("relevant", "carbon offset registry audit found irregularities", index=0),
        make_chunk("other", "cafeteria menu rotation schedule", index=1, source="b.pdf"),
    ]
    first = await service.rerank("carbon offset registry audit", chunks, k=2)
    second = await service.rerank("carbon offset registry audit", chunks, k=2)

    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    assert first[0].chunk_id == "relevant"
    assert all(0.0 <= c.rerank_score <= 1.0 for c in first)


@pytest.mark.asyncio
async def test_rerank_honours_k_and_empty_input(service):
    chunks = [make_chunk(f"c{i}", f"green claim {i}", index=i) for i in range(5)]
    assert await service.rerank("green claim", [], k=3) == []
    assert len(await service.rerank("green claim", chunks, k=2)) == 2


@pytest.mark.asyncio
async def test_injected_reranker_is_used_and_lazy():
    """A lazily-loaded re-ranker is only built on first use, then reused."""
    load_count = {"n": 0}

    def loader():
        load_count["n"] += 1

        def score(query: str, texts: list[str]) -> list[float]:
            # Reverse preference: later chunks score higher.
            return [i / max(1, len(texts) - 1) for i in range(len(texts))]

        return score

    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]),
        embedding_service=FakeEmbeddingService(),
        reranker_loader=loader,
    )
    assert load_count["n"] == 0, "re-ranker must not load at construction"

    chunks = [make_chunk("first", "alpha text", index=0), make_chunk("second", "beta text", index=1)]
    ranked = await svc.rerank("alpha", chunks, k=2)
    assert ranked[0].chunk_id == "second"
    assert load_count["n"] == 1

    await svc.rerank("alpha", chunks, k=2)
    assert load_count["n"] == 1, "loader should be invoked once"


@pytest.mark.asyncio
async def test_broken_reranker_falls_back():
    """A failing re-ranker degrades to the lexical fallback instead of raising."""

    def boom(query, texts):
        raise RuntimeError("no model available")

    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]),
        embedding_service=FakeEmbeddingService(),
        reranker=boom,
    )
    chunks = [
        make_chunk("relevant", "carbon offset registry audit", index=0),
        make_chunk("other", "cafeteria menu", index=1, source="b.pdf"),
    ]
    ranked = await svc.rerank("carbon offset registry audit", chunks, k=2)
    assert ranked[0].chunk_id == "relevant"


# ---------------------------------------------------------------------------
# retrieve() plumbing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_empty_query_and_empty_session():
    svc = HybridRetrievalService(
        vector_store=FakeVectorStore([]), embedding_service=FakeEmbeddingService()
    )
    assert await svc.retrieve("", "s1") == []
    assert await svc.retrieve("   ", "s1") == []
    assert await svc.retrieve("carbon neutral", "s1") == []


@pytest.mark.asyncio
async def test_retrieve_uses_injected_embedding_service():
    """No embedding model is instantiated — the injected fake is used."""
    corpus = [make_chunk("c1", "carbon neutral certified by auditor")]
    embedder = FakeEmbeddingService()
    svc = HybridRetrievalService(
        vector_store=FakeVectorStore(corpus, distances={"c1": 0.1}),
        embedding_service=embedder,
    )
    results = await svc.retrieve("carbon neutral", "s1", k=3, max_tokens=100000)
    assert embedder.calls == ["carbon neutral"]
    assert [r.chunk_id for r in results] == ["c1"]
    assert results[0].semantic_score == pytest.approx(0.9)
