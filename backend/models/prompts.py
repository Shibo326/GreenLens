"""
Data models for prompt versioning, experimentation, and promotion.

Field definitions mirror the AI Advanced Training design document
(Data Models section) exactly.

`MetricsResult` is owned by `models/evaluation.py` (Task 3) and is imported
here rather than redefined, so that prompt evaluation scores and evaluation
framework output share a single schema.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.evaluation import MetricsResult


class PromptVersion(BaseModel):
    """A single versioned prompt, optionally flagged as the production one."""

    name: str
    version: str
    content: str
    is_production: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_scores: MetricsResult | None = None


class PromptExperiment(BaseModel):
    """One recorded execution of a prompt version, with cost/latency telemetry."""

    id: str
    prompt_name: str
    prompt_version: str
    input_hash: str
    output_hash: str
    latency_ms: int
    token_count: int
    evaluation_scores: MetricsResult | None = None
    run_at: datetime = Field(default_factory=datetime.utcnow)


class PromptEvaluationResult(BaseModel):
    """Head-to-head comparison of a candidate prompt against production."""

    candidate_version: str
    production_version: str
    candidate_metrics: MetricsResult
    production_metrics: MetricsResult
    is_improvement: bool
    recommendation: str
