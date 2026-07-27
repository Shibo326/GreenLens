"""
EvaluationFramework — runs labeled test suites against the AI, scores the
results (precision / recall / F1 per severity level), compares prompt
variants, and detects regressions against a baseline report.

All LLM calls run in parallel with a semaphore cap, matching the concurrency
pattern used by services/analysis_service.py.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime
from uuid import uuid4

from models.evaluation import (
    EvaluationReport,
    MetricsResult,
    Misclassification,
    PromptComparisonReport,
    RegressionResult,
)
from models.training import SeverityLevel, TrainingExample
from services.llm_service import _strip_json_fences

logger = logging.getLogger(__name__)

# Default directory for persisted evaluation reports
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation")

# Max concurrent LLM calls — mirrors LLMService's semaphore cap of 3
MAX_CONCURRENT_CALLS = 3

# Per-call timeout (seconds)
LLM_CALL_TIMEOUT = 80

# F1 drop (absolute) that counts as a regression — 5 percentage points
REGRESSION_THRESHOLD = 0.05

# Sentinel used when a prediction could not be obtained or parsed
UNKNOWN_LABEL = "UNKNOWN"

DEFAULT_PROMPT_VERSION = "production"

_EVAL_SYSTEM_PROMPT = (
    "You are a greenwashing detection evaluator. Classify the sustainability "
    "claim you are given. Respond ONLY with valid JSON of the form "
    '{"verdict": "MISLEADING|VAGUE|UNVERIFIED|SUBSTANTIATED", '
    '"severity": "HIGH|MEDIUM|LOW"}.'
)


class EvaluationFramework:
    """
    Runs test suites of labeled examples against the AI and computes
    accuracy metrics.

    Dependencies are injected so tests can pass fakes — no network access is
    performed by this class itself.
    """

    def __init__(
        self,
        llm_service,
        training_pipeline,
        data_dir: str | None = None,
        max_concurrency: int = MAX_CONCURRENT_CALLS,
    ):
        self.llm_service = llm_service
        self.training_pipeline = training_pipeline
        self.data_dir = data_dir or _DATA_DIR
        self.max_concurrency = max(1, max_concurrency)
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(
            f"EvaluationFramework initialized — data dir: {self.data_dir}, "
            f"max concurrency: {self.max_concurrency}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_evaluation(
        self, prompt_version: str | None = None, max_examples: int = 50
    ) -> EvaluationReport:
        """
        Run the full test suite and produce a scored report.

        LLM calls execute in parallel via asyncio.gather with a semaphore cap.
        The resulting report is persisted as JSON under `self.data_dir`.
        """
        version = prompt_version or DEFAULT_PROMPT_VERSION
        started = time.perf_counter()

        examples = await self.training_pipeline.get_examples(limit=max_examples)
        examples = list(examples)[:max_examples]

        predictions, ground_truth, misclassifications, latencies = (
            await self._evaluate_examples(examples, _EVAL_SYSTEM_PROMPT)
        )

        metrics = self.compute_metrics(predictions, ground_truth)
        metrics.avg_response_time_ms = (
            sum(latencies) / len(latencies) if latencies else 0.0
        )

        report = EvaluationReport(
            id=str(uuid4()),
            prompt_version=version,
            run_at=datetime.utcnow(),
            metrics=metrics,
            misclassifications=misclassifications,
            total_examples=len(examples),
            duration_seconds=round(time.perf_counter() - started, 4),
        )

        self._persist_report(report)
        logger.info(
            f"Evaluation {report.id} complete — {report.total_examples} examples, "
            f"accuracy={metrics.overall_accuracy:.3f}, f1={metrics.overall_f1:.3f}"
        )
        return report

    async def compare_prompts(
        self, prompt_a: str, prompt_b: str
    ) -> PromptComparisonReport:
        """
        Run the same inputs through two prompts and compare their metrics.

        `prompt_a` / `prompt_b` are prompt contents (short strings are treated
        as version identifiers and used verbatim as the reported version).
        """
        examples = await self.training_pipeline.get_examples(limit=50)
        examples = list(examples)

        preds_a, truth_a, _, latencies_a = await self._evaluate_examples(
            examples, prompt_a
        )
        preds_b, truth_b, _, latencies_b = await self._evaluate_examples(
            examples, prompt_b
        )

        metrics_a = self.compute_metrics(preds_a, truth_a)
        metrics_a.avg_response_time_ms = (
            sum(latencies_a) / len(latencies_a) if latencies_a else 0.0
        )
        metrics_b = self.compute_metrics(preds_b, truth_b)
        metrics_b.avg_response_time_ms = (
            sum(latencies_b) / len(latencies_b) if latencies_b else 0.0
        )

        label_a = _prompt_label(prompt_a)
        label_b = _prompt_label(prompt_b)

        if metrics_a.overall_f1 > metrics_b.overall_f1:
            winner = label_a
        elif metrics_b.overall_f1 > metrics_a.overall_f1:
            winner = label_b
        else:
            winner = None

        return PromptComparisonReport(
            prompt_a_version=label_a,
            prompt_b_version=label_b,
            prompt_a_metrics=metrics_a,
            prompt_b_metrics=metrics_b,
            winner=winner,
        )

    async def check_regression(
        self, current: EvaluationReport, baseline: EvaluationReport
    ) -> RegressionResult:
        """
        Compare current scores against a baseline, flagging any category whose
        F1 dropped by more than 5 percentage points.
        """
        details: dict[str, dict[str, float]] = {}
        regressed: list[str] = []

        baseline_cats = baseline.metrics.per_category
        current_cats = current.metrics.per_category

        for category in baseline_cats:
            baseline_f1 = float(baseline_cats.get(category, {}).get("f1", 0.0))
            current_f1 = float(current_cats.get(category, {}).get("f1", 0.0))
            delta = current_f1 - baseline_f1
            drop = baseline_f1 - current_f1

            details[category] = {
                "baseline_f1": baseline_f1,
                "current_f1": current_f1,
                "delta": delta,
            }

            if drop > REGRESSION_THRESHOLD:
                regressed.append(category)

        return RegressionResult(
            has_regression=len(regressed) > 0,
            regressed_categories=regressed,
            details=details,
        )

    def compute_metrics(
        self, predictions: list[str], ground_truth: list[str]
    ) -> MetricsResult:
        """
        Compute precision, recall, and F1 per category (severity level).

        Division-by-zero safe: when TP+FP == 0 or TP+FN == 0 the metric is
        0.0, and F1 is 0.0 when precision + recall == 0.
        """
        if len(predictions) != len(ground_truth):
            raise ValueError(
                f"predictions ({len(predictions)}) and ground_truth "
                f"({len(ground_truth)}) must have the same length"
            )

        categories = sorted(set(ground_truth) | set(predictions))
        per_category: dict[str, dict[str, float]] = {}
        f1_scores: list[float] = []

        for category in categories:
            tp = sum(
                1
                for pred, truth in zip(predictions, ground_truth)
                if pred == category and truth == category
            )
            fp = sum(
                1
                for pred, truth in zip(predictions, ground_truth)
                if pred == category and truth != category
            )
            fn = sum(
                1
                for pred, truth in zip(predictions, ground_truth)
                if pred != category and truth == category
            )

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            per_category[category] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": float(tp + fn),
                "true_positives": float(tp),
                "false_positives": float(fp),
                "false_negatives": float(fn),
            }
            f1_scores.append(f1)

        total = len(ground_truth)
        correct = sum(
            1 for pred, truth in zip(predictions, ground_truth) if pred == truth
        )
        overall_accuracy = correct / total if total > 0 else 0.0
        overall_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

        return MetricsResult(
            per_category=per_category,
            overall_accuracy=overall_accuracy,
            overall_f1=overall_f1,
            avg_response_time_ms=0.0,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _evaluate_examples(
        self, examples: list[TrainingExample], system_prompt: str
    ) -> tuple[list[str], list[str], list[Misclassification], list[float]]:
        """
        Run every example through the LLM in parallel (semaphore-capped) and
        collect predictions, ground truth, misclassifications, and latencies.
        """
        if not examples:
            return [], [], [], []

        semaphore = asyncio.Semaphore(self.max_concurrency)

        results = await asyncio.gather(
            *(
                self._classify_one(example, system_prompt, semaphore)
                for example in examples
            ),
            return_exceptions=True,
        )

        predictions: list[str] = []
        ground_truth: list[str] = []
        misclassifications: list[Misclassification] = []
        latencies: list[float] = []

        for example, result in zip(examples, results):
            expected = _severity_value(example.severity)
            ground_truth.append(expected)

            if isinstance(result, BaseException):
                logger.warning(
                    f"Evaluation call failed for example {example.id}: {result}"
                )
                predicted, latency_ms = UNKNOWN_LABEL, 0.0
            else:
                predicted, latency_ms = result

            predictions.append(predicted)
            latencies.append(latency_ms)

            if predicted != expected:
                misclassifications.append(
                    Misclassification(
                        example_id=example.id,
                        expected=expected,
                        predicted=predicted,
                        input_claim=_input_claim(example),
                    )
                )

        return predictions, ground_truth, misclassifications, latencies

    async def _classify_one(
        self,
        example: TrainingExample,
        system_prompt: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, float]:
        """Classify a single example, returning (predicted_severity, latency_ms)."""
        user_prompt = _input_claim(example)
        async with semaphore:
            started = time.perf_counter()
            try:
                raw = await asyncio.wait_for(
                    self.llm_service.complete(
                        system_prompt,
                        user_prompt,
                        max_tokens=200,
                        temperature=0.0,
                        fast=True,
                    ),
                    timeout=LLM_CALL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Evaluation LLM call timed out after {LLM_CALL_TIMEOUT}s "
                    f"(example {example.id})"
                )
                return UNKNOWN_LABEL, (time.perf_counter() - started) * 1000.0
            latency_ms = (time.perf_counter() - started) * 1000.0

        return _parse_severity(raw), latency_ms

    def _persist_report(self, report: EvaluationReport) -> str:
        """Write an evaluation report to disk as JSON (UTF-8)."""
        path = os.path.join(self.data_dir, f"{report.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
        return path

    def _load_report(self, report_id: str) -> EvaluationReport | None:
        """Load a persisted evaluation report by id, or None if missing."""
        path = os.path.join(self.data_dir, f"{report_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return EvaluationReport.model_validate(json.load(f))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _severity_value(severity) -> str:
    """Normalize a SeverityLevel (or raw string) to its string value."""
    if isinstance(severity, SeverityLevel):
        return severity.value
    return str(severity)


def _input_claim(example: TrainingExample) -> str:
    """Extract the user-facing claim text from an example's messages."""
    for message in example.messages:
        if message.role == "user":
            return message.content
    return example.messages[0].content if example.messages else ""


def _parse_severity(raw: str) -> str:
    """
    Extract a severity label from an LLM response.

    Tries JSON first, then falls back to a plain-text scan. Returns
    UNKNOWN_LABEL when nothing valid is found.
    """
    if not raw:
        return UNKNOWN_LABEL

    valid = {level.value for level in SeverityLevel}
    cleaned = _strip_json_fences(raw)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            candidate = data.get("severity") or data.get("severity_level") or ""
            candidate = str(candidate).strip().upper()
            if candidate in valid:
                return candidate
    except (json.JSONDecodeError, ValueError):
        pass

    upper = raw.upper()
    for level in ("HIGH", "MEDIUM", "LOW"):
        if level in upper:
            return level

    return UNKNOWN_LABEL


def _prompt_label(prompt: str) -> str:
    """
    Derive a stable label for a prompt.

    Short strings look like version identifiers and are used verbatim; longer
    prompt bodies get a deterministic content hash.
    """
    text = (prompt or "").strip()
    if not text:
        return "unknown"
    if len(text) <= 32 and "\n" not in text:
        return text
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
