"""
Data models for the evaluation framework of the AI Advanced Training subsystem.

Covers accuracy metrics, evaluation reports, regression detection, and
prompt A/B comparison results for the GreenLens greenwashing detector.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MetricsResult(BaseModel):
    """Precision / recall / F1 metrics, broken down per category."""

    per_category: dict[str, dict[str, float]]
    overall_accuracy: float
    overall_f1: float
    avg_response_time_ms: float


class Misclassification(BaseModel):
    """A single example the model got wrong."""

    example_id: str
    expected: str
    predicted: str
    input_claim: str


class EvaluationReport(BaseModel):
    """Scored result of one evaluation run over the labeled test suite."""

    id: str
    prompt_version: str
    run_at: datetime
    metrics: MetricsResult
    misclassifications: list[Misclassification]
    total_examples: int
    duration_seconds: float


class RegressionResult(BaseModel):
    """Outcome of comparing a current report against a baseline report."""

    has_regression: bool
    regressed_categories: list[str]
    details: dict[str, dict[str, float]]


class PromptComparisonReport(BaseModel):
    """Side-by-side comparison of two prompts over identical inputs."""

    prompt_a_version: str
    prompt_b_version: str
    prompt_a_metrics: MetricsResult
    prompt_b_metrics: MetricsResult
    winner: str | None
