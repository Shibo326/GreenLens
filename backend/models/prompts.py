"""Data models for prompt versioning."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from models.evaluation import MetricsResult

class PromptVersion(BaseModel):
    name: str
    version: str
    content: str
    is_production: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    evaluation_scores: MetricsResult | None = None

class PromptExperiment(BaseModel):
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
    candidate_version: str
    production_version: str
    candidate_metrics: MetricsResult
    production_metrics: MetricsResult
    is_improvement: bool
    recommendation: str
