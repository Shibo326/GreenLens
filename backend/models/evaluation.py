"""Data models for the evaluation framework."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel

class MetricsResult(BaseModel):
    per_category: dict[str, dict[str, float]]
    overall_accuracy: float
    overall_f1: float
    avg_response_time_ms: float

class Misclassification(BaseModel):
    example_id: str
    expected: str
    predicted: str
    input_claim: str

class EvaluationReport(BaseModel):
    id: str
    prompt_version: str
    run_at: datetime
    metrics: MetricsResult
    misclassifications: list[Misclassification]
    total_examples: int
    duration_seconds: float

class RegressionResult(BaseModel):
    has_regression: bool
    regressed_categories: list[str]
    details: dict[str, dict[str, float]]

class PromptComparisonReport(BaseModel):
    prompt_a_version: str
    prompt_b_version: str
    prompt_a_metrics: MetricsResult
    prompt_b_metrics: MetricsResult
    winner: str | None
