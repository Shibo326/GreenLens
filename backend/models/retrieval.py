"""
Data models for hybrid retrieval (semantic + BM25) in the AI Advanced
Training subsystem.

`ScoredChunk` represents a chunk scored by a single retrieval method.
`RankedChunk` represents a chunk after fusion, re-ranking, and boosting.

Field definitions mirror the design document's Data Models section exactly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ScoredChunk(BaseModel):
    """A chunk scored by exactly one retrieval method."""

    chunk_id: str
    text: str
    source_document: str
    score: float
    method: Literal["semantic", "bm25"]


class RankedChunk(BaseModel):
    """A chunk after hybrid fusion, re-ranking, and entity boosting."""

    chunk_id: str
    text: str
    source_document: str
    document_type: str
    combined_score: float
    semantic_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
