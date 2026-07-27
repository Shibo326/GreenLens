"""
Hybrid retrieval service: combines the existing semantic vector search with
BM25 keyword search, cosine-distance filtering, named-entity boosting,
optional cross-encoder re-ranking, and diversity-aware selection.

Design notes
------------
* `VectorStore` and `EmbeddingService` are injected through the constructor and
  created lazily only when not supplied, so tests can pass fakes and never load
  a model or open a Chroma client.
* Re-ranking is optional and lazy. When no re-ranker is injected, a
  deterministic pure-Python lexical overlap score is used. Nothing is
  downloaded at import time or during tests.
* `rank_bm25` is used when importable; otherwise a small pure-Python BM25
  Okapi implementation with identical scoring semantics is used.
* `k` is the per-method retrieval depth. The result set is guaranteed to keep
  every candidate from the semantic top-k and the BM25 top-k that survives
  distance / document-type filtering, subject only to the token budget
  (see Property 16). The token budget, not `k`, bounds the final size.
"""

from __future__ import annotations

import logging
import math
import re
from collections import OrderedDict
from typing import Any, Callable, Iterable, Sequence

from models.document import Chunk
from models.retrieval import RankedChunk, ScoredChunk

logger = logging.getLogger(__name__)

# Chunks whose cosine distance from the query exceeds this are irrelevant.
MAX_COSINE_DISTANCE = 0.7

# Fusion weights for the combined score.
SEMANTIC_WEIGHT = 0.4
BM25_WEIGHT = 0.3
RERANK_WEIGHT = 0.3

# Additive boost per distinct named entity from the query found in a chunk.
ENTITY_BOOST = 0.15
MAX_ENTITY_BOOST = 0.45

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+", re.UNICODE)

# Capitalised word sequences and acronyms, e.g. "Shell", "Nestle SA", "FTC".
_ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*\b")

# Words that look like entities at the start of a sentence but are not.
_ENTITY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "did", "do",
    "does", "for", "from", "has", "have", "how", "i", "if", "in", "is", "it",
    "its", "of", "on", "or", "our", "that", "the",
    "their", "there", "these", "this", "to", "was", "we", "were", "what",
    "when", "where", "which", "who", "why", "will", "with", "you", "your",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenisation shared by BM25 and the fallback re-ranker."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class _PurePythonBM25:
    """
    Minimal BM25 Okapi implementation used when `rank_bm25` is unavailable.

    Scoring matches rank_bm25.BM25Okapi (k1=1.5, b=0.75, epsilon=0.25 IDF floor)
    closely enough for ranking purposes.
    """

    def __init__(self, corpus: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = [list(doc) for doc in corpus]
        self.corpus_size = len(self.corpus)
        self.doc_len = [len(doc) for doc in self.corpus]
        self.avgdl = (sum(self.doc_len) / self.corpus_size) if self.corpus_size else 0.0

        self.doc_freqs: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for doc in self.corpus:
            freqs: dict[str, int] = {}
            for term in doc:
                freqs[term] = freqs.get(term, 0) + 1
            self.doc_freqs.append(freqs)
            for term in freqs:
                df[term] = df.get(term, 0) + 1

        self.idf: dict[str, float] = {}
        for term, freq in df.items():
            value = math.log(self.corpus_size - freq + 0.5) - math.log(freq + 0.5)
            # Floor negative IDF the way rank_bm25 does, so common terms
            # never subtract from a document's score.
            self.idf[term] = value if value > 0 else 0.25 * 0.5

    def get_scores(self, query_tokens: Sequence[str]) -> list[float]:
        scores = [0.0] * self.corpus_size
        for index, freqs in enumerate(self.doc_freqs):
            length = self.doc_len[index]
            total = 0.0
            for term in query_tokens:
                if term not in freqs:
                    continue
                tf = freqs[term]
                denom = tf + self.k1 * (
                    1 - self.b + self.b * (length / self.avgdl if self.avgdl else 0.0)
                )
                total += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / (denom or 1.0)
            scores[index] = total
        return scores


def _build_bm25(tokenized_corpus: Sequence[Sequence[str]]):
    """Return a BM25 index, preferring `rank_bm25` and falling back locally."""
    try:
        from rank_bm25 import BM25Okapi  # type: ignore

        return BM25Okapi(list(tokenized_corpus))
    except Exception:  # pragma: no cover - exercised only without rank_bm25
        logger.debug("rank_bm25 unavailable; using pure-Python BM25 fallback")
        return _PurePythonBM25(tokenized_corpus)


class HybridRetrievalService:
    """Hybrid (semantic + keyword) retrieval with re-ranking and diversity."""

    def __init__(
        self,
        vector_store: Any | None = None,
        embedding_service: Any | None = None,
        reranker: Any | None = None,
        reranker_loader: Callable[[], Any] | None = None,
        max_distance: float = MAX_COSINE_DISTANCE,
    ):
        """
        Args:
            vector_store: existing `VectorStore` (or fake). Created lazily if None.
            embedding_service: existing `EmbeddingService` (or fake). Created lazily.
            reranker: optional cross-encoder-like object or callable. Either
                `callable(query, texts) -> list[float]` or an object exposing
                `predict(list[tuple[str, str]]) -> list[float]`.
            reranker_loader: optional zero-arg factory invoked on first use to
                build the re-ranker. Never called at import time.
            max_distance: cosine distance cut-off for semantic results.
        """
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._reranker = reranker
        self._reranker_loader = reranker_loader
        self._reranker_loaded = reranker is not None
        self.max_distance = max_distance

    # ------------------------------------------------------------------
    # Lazily resolved collaborators
    # ------------------------------------------------------------------

    @property
    def vector_store(self):
        if self._vector_store is None:
            from services.vector_store import VectorStore

            self._vector_store = VectorStore()
        return self._vector_store

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from services.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def _get_reranker(self):
        """Resolve the re-ranker lazily; returns None to use the fallback."""
        if not self._reranker_loaded:
            self._reranker_loaded = True
            if self._reranker_loader is not None:
                try:
                    self._reranker = self._reranker_loader()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(f"Re-ranker unavailable, using fallback: {exc}")
                    self._reranker = None
        return self._reranker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        session_id: str,
        k: int = 5,
        max_tokens: int = 4000,
        doc_type_filter: str | None = None,
    ) -> list[RankedChunk]:
        """
        Hybrid retrieval with re-ranking and diversity selection.

        Semantic top-k and BM25 top-k candidates are merged, distance-filtered,
        optionally restricted to a document type, re-ranked, entity-boosted, and
        finally trimmed to the token budget with diversity-aware selection.
        """
        if not query or not query.strip():
            return []

        embedding = self.embedding_service.embed(query)
        semantic_chunks = self.filter_by_distance(
            self.vector_store.query_top_k(session_id, embedding, k=k) or []
        )

        corpus = self.vector_store.get_all_chunks(session_id) or []
        bm25_scored = self.bm25_search(query, corpus, k=k)

        # Merge candidates, remembering per-method scores.
        candidates: "OrderedDict[str, Chunk]" = OrderedDict()
        semantic_scores: dict[str, float] = {}
        bm25_scores: dict[str, float] = {}

        for chunk in semantic_chunks:
            candidates.setdefault(chunk.id, chunk)
            distance = chunk.distance
            if distance is not None:
                semantic_scores[chunk.id] = max(0.0, 1.0 - float(distance))

        by_id = {chunk.id: chunk for chunk in corpus}
        for scored in bm25_scored:
            chunk = by_id.get(scored.chunk_id)
            if chunk is None:
                continue
            candidates.setdefault(chunk.id, chunk)
            bm25_scores[chunk.id] = scored.score

        if doc_type_filter is not None:
            candidates = OrderedDict(
                (cid, c) for cid, c in candidates.items()
                if c.document_type == doc_type_filter
            )

        if not candidates:
            return []

        chunk_list = list(candidates.values())
        ranked = await self.rerank(query, chunk_list, k=len(chunk_list))

        # Fuse semantic, BM25, re-rank scores and the named-entity boost.
        max_bm25 = max((v for v in bm25_scores.values()), default=0.0)
        entities = self.extract_entities(query)

        for item in ranked:
            sem = semantic_scores.get(item.chunk_id)
            bm25 = bm25_scores.get(item.chunk_id)
            item.semantic_score = sem
            item.bm25_score = bm25
            bm25_norm = (bm25 / max_bm25) if (bm25 and max_bm25 > 0) else 0.0
            combined = (
                SEMANTIC_WEIGHT * (sem or 0.0)
                + BM25_WEIGHT * bm25_norm
                + RERANK_WEIGHT * (item.rerank_score or 0.0)
            )
            item.combined_score = round(
                combined + self.entity_boost(item.text, entities), 6
            )

        return self.select_diverse(ranked, budget_tokens=max_tokens)

    def bm25_search(
        self, query: str, chunks: list[Chunk], k: int = 10
    ) -> list[ScoredChunk]:
        """Keyword-based BM25 search over chunk texts."""
        if not query or not query.strip() or not chunks:
            return []

        tokenized_corpus = [_tokenize(chunk.text) for chunk in chunks]
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        query_token_set = set(query_tokens)
        index = _build_bm25(tokenized_corpus)
        scores = list(index.get_scores(query_tokens))

        results = [
            ScoredChunk(
                chunk_id=chunk.id,
                text=chunk.text,
                source_document=chunk.source_document,
                score=float(score),
                method="bm25",
            )
            for chunk, score, tokens in zip(chunks, scores, tokenized_corpus)
            if query_token_set & set(tokens)  # At least one query term present
        ]
        results.sort(key=lambda s: (-s.score, s.chunk_id))
        return results[: max(0, k)]

    async def rerank(
        self, query: str, chunks: list[Chunk], k: int = 5
    ) -> list[RankedChunk]:
        """
        Re-rank chunks using a cross-encoder when one is available, otherwise a
        deterministic pure-Python lexical overlap score.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        scores = self._rerank_scores(query, texts)

        ranked = [
            RankedChunk(
                chunk_id=chunk.id,
                text=chunk.text,
                source_document=chunk.source_document,
                document_type=chunk.document_type,
                combined_score=float(score),
                semantic_score=(
                    max(0.0, 1.0 - float(chunk.distance))
                    if chunk.distance is not None
                    else None
                ),
                rerank_score=float(score),
            )
            for chunk, score in zip(chunks, scores)
        ]
        ranked.sort(key=lambda c: (-c.rerank_score, c.chunk_id))
        return ranked[: max(0, k)]

    def select_diverse(
        self, chunks: list[RankedChunk], budget_tokens: int = 4000
    ) -> list[RankedChunk]:
        """
        Select chunks maximising source diversity within the token budget.

        Chunks are visited round-robin across source documents (best chunk of
        each source first), so the selection covers at least as many distinct
        sources as a naive top-k-by-score pass.
        """
        if not chunks:
            return []

        ordered = sorted(chunks, key=lambda c: (-c.combined_score, c.chunk_id))

        groups: "OrderedDict[str, list[RankedChunk]]" = OrderedDict()
        for chunk in ordered:
            groups.setdefault(chunk.source_document, []).append(chunk)

        round_robin: list[RankedChunk] = []
        depth = 0
        while True:
            added = False
            for items in groups.values():
                if depth < len(items):
                    round_robin.append(items[depth])
                    added = True
            if not added:
                break
            depth += 1

        selected: list[RankedChunk] = []
        used = 0
        for chunk in round_robin:
            cost = self.estimate_tokens(chunk.text)
            if used + cost <= budget_tokens:
                selected.append(chunk)
                used += cost

        if not selected:
            # Always return the single best chunk rather than nothing.
            selected = [round_robin[0]]

        selected.sort(key=lambda c: (-c.combined_score, c.chunk_id))
        return selected

    # ------------------------------------------------------------------
    # Helpers (public so tests can exercise them directly)
    # ------------------------------------------------------------------

    def filter_by_distance(self, chunks: Iterable[Chunk]) -> list[Chunk]:
        """
        Drop chunks whose cosine distance exceeds the threshold.

        Chunks without a distance (e.g. BM25-only candidates) are kept.
        The result is always a subset of the input.
        """
        return [
            chunk
            for chunk in chunks
            if chunk.distance is None or float(chunk.distance) <= self.max_distance
        ]

    @staticmethod
    def extract_entities(query: str) -> list[str]:
        """
        Heuristically extract named entities (capitalised spans, acronyms) from
        a query. Pure Python, no models, deterministic.
        """
        if not query:
            return []
        entities: list[str] = []
        for match in _ENTITY_RE.findall(query):
            candidate = match.strip()
            if len(candidate) < 2:
                continue
            words = candidate.split()
            if all(w.lower() in _ENTITY_STOPWORDS for w in words):
                continue
            # Strip leading stopwords (e.g. sentence-initial "Did" in
            # "Did Northwind Energy mislead...") to isolate real entities.
            while words and words[0].lower() in _ENTITY_STOPWORDS:
                words = words[1:]
            if not words:
                continue
            candidate = " ".join(words)
            if len(candidate) < 2:
                continue
            if candidate not in entities:
                entities.append(candidate)
        return entities

    @staticmethod
    def entity_boost(text: str, entities: Sequence[str]) -> float:
        """Additive score boost for each query entity appearing verbatim."""
        if not text or not entities:
            return 0.0
        hits = sum(1 for entity in entities if entity in text)
        return min(MAX_ENTITY_BOOST, hits * ENTITY_BOOST)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Approximate token count (~0.75 words per token, matching chunking)."""
        words = len((text or "").split())
        if words == 0:
            return 1
        return max(1, int(round(words / 0.75)))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rerank_scores(self, query: str, texts: list[str]) -> list[float]:
        reranker = self._get_reranker()
        if reranker is not None:
            try:
                if hasattr(reranker, "predict"):
                    raw = reranker.predict([(query, text) for text in texts])
                else:
                    raw = reranker(query, texts)
                scores = [float(s) for s in raw]
                if len(scores) == len(texts):
                    return scores
                logger.warning("Re-ranker returned wrong score count; using fallback")
            except Exception as exc:
                logger.warning(f"Re-ranker failed, using fallback: {exc}")
        return [self._lexical_score(query, text) for text in texts]

    @staticmethod
    def _lexical_score(query: str, text: str) -> float:
        """
        Deterministic offline relevance score in [0, 1]: the fraction of query
        terms present in the chunk, with a small density term as a tie-breaker.
        """
        query_terms = set(_tokenize(query))
        if not query_terms:
            return 0.0
        text_tokens = _tokenize(text)
        if not text_tokens:
            return 0.0
        text_terms = set(text_tokens)
        coverage = len(query_terms & text_terms) / len(query_terms)
        matches = sum(1 for t in text_tokens if t in query_terms)
        density = matches / len(text_tokens)
        return round(0.9 * coverage + 0.1 * density, 6)
