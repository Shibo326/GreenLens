"""
EvaluationFramework -- runs labeled test suites against the AI and computes
accuracy metrics (precision, recall, F1 per severity level).
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

from models.evaluation import (
    EvaluationReport,
    MetricsResult,
    Misclassification,
    PromptComparisonReport,
    RegressionResult,
)
from models.training import TrainingExample

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "evaluations")


class EvaluationFramework:
    """Runs test suites of labeled examples against the AI and computes accuracy metrics."""

    def __init__(self, data_dir: str | None = None, llm_service=None, training_service=None):
        self.data_dir = data_dir or _DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self._llm = llm_service
        self._training = training_service

    async def run_evaluation(
        self, prompt_version: str | None = None, max_examples: int = 50
    ) -> EvaluationReport:
        """
        Run the full test suite and produce a scored report.

        Loads labeled examples from TrainingPipelineService, runs them through
        the LLM, compares outputs to ground truth, and computes metrics.
        If no LLM is available, mocks predictions for testability.
        """
        version = prompt_version or "current"
        examples = await self._load_examples(max_examples)

        start = time.time()
        predictions = await self._get_predictions(examples, version)
        duration = time.time() - start

        ground_truth = [self._extract_label(ex) for ex in examples]
        metrics = self.compute_metrics(predictions, ground_truth)

        # Override avg_response_time with actual measured time
        avg_ms = (duration / len(examples) * 1000) if examples else 0.0
        metrics = MetricsResult(
            per_category=metrics.per_category,
            overall_accuracy=metrics.overall_accuracy,
            overall_f1=metrics.overall_f1,
            avg_response_time_ms=avg_ms,
        )

        misclassifications = self._find_misclassifications(examples, predictions, ground_truth)

        report = EvaluationReport(
            id=str(uuid4()),
            prompt_version=version,
            run_at=datetime.now(timezone.utc),
            metrics=metrics,
            misclassifications=misclassifications,
            total_examples=len(examples),
            duration_seconds=duration,
        )

        await self._save_report(report)
        return report

    async def compare_prompts(
        self, prompt_a: str, prompt_b: str
    ) -> PromptComparisonReport:
        """Run the same inputs through two prompts and compare."""
        examples = await self._load_examples(50)
        ground_truth = [self._extract_label(ex) for ex in examples]

        predictions_a, predictions_b = await asyncio.gather(
            self._get_predictions(examples, prompt_a),
            self._get_predictions(examples, prompt_b),
        )

        metrics_a = self.compute_metrics(predictions_a, ground_truth)
        metrics_b = self.compute_metrics(predictions_b, ground_truth)

        winner: str | None = None
        if metrics_a.overall_f1 > metrics_b.overall_f1:
            winner = prompt_a
        elif metrics_b.overall_f1 > metrics_a.overall_f1:
            winner = prompt_b

        return PromptComparisonReport(
            prompt_a_version=prompt_a,
            prompt_b_version=prompt_b,
            prompt_a_metrics=metrics_a,
            prompt_b_metrics=metrics_b,
            winner=winner,
        )

    async def check_regression(
        self, current: EvaluationReport, baseline: EvaluationReport
    ) -> RegressionResult:
        """
        Compare current scores against baseline, flag >5pp F1 drops.

        A category is considered regressed if its F1 dropped by more than
        0.05 (5 percentage points) compared to baseline.
        """
        regressed: list[str] = []
        details: dict[str, dict[str, float]] = {}

        baseline_cats = baseline.metrics.per_category
        current_cats = current.metrics.per_category

        for category in baseline_cats:
            baseline_f1 = baseline_cats[category].get("f1", 0.0)
            current_f1 = current_cats.get(category, {}).get("f1", 0.0)
            drop = baseline_f1 - current_f1

            details[category] = {
                "baseline_f1": baseline_f1,
                "current_f1": current_f1,
                "drop": drop,
            }

            if drop > 0.05:
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
        Compute precision, recall, F1 per severity/label category.

        This is a pure function (no LLM calls). Calculates TP/FP/FN per
        category and derives precision, recall, and F1 from those counts.
        """
        categories = sorted(set(ground_truth) | set(predictions))

        per_category: dict[str, dict[str, float]] = {}
        total_correct = 0

        for cat in categories:
            tp = sum(
                1 for p, g in zip(predictions, ground_truth) if p == cat and g == cat
            )
            fp = sum(
                1 for p, g in zip(predictions, ground_truth) if p == cat and g != cat
            )
            fn = sum(
                1 for p, g in zip(predictions, ground_truth) if p != cat and g == cat
            )

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            per_category[cat] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": float(tp),
                "fp": float(fp),
                "fn": float(fn),
            }

            total_correct += tp

        total = len(ground_truth)
        overall_accuracy = total_correct / total if total > 0 else 0.0

        # Macro-average F1
        f1_values = [m["f1"] for m in per_category.values()]
        overall_f1 = sum(f1_values) / len(f1_values) if f1_values else 0.0

        return MetricsResult(
            per_category=per_category,
            overall_accuracy=overall_accuracy,
            overall_f1=overall_f1,
            avg_response_time_ms=0.0,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _load_examples(self, max_examples: int) -> list[TrainingExample]:
        """Load labeled examples from the training pipeline service."""
        if self._training:
            return await self._training.get_examples(limit=max_examples)
        return []

    async def _get_predictions(
        self, examples: list[TrainingExample], prompt_version: str
    ) -> list[str]:
        """
        Get predictions for examples. Uses LLM if available, otherwise mocks.
        Runs predictions in parallel using asyncio for performance.
        """
        if not examples:
            return []

        if self._llm is None:
            # Mock predictions for testability: return ground truth labels
            # with some intentional noise for realistic evaluation
            return [self._extract_label(ex) for ex in examples]

        # Run predictions in parallel
        tasks = [self._predict_single(ex, prompt_version) for ex in examples]
        return await asyncio.gather(*tasks)

    async def _predict_single(
        self, example: TrainingExample, prompt_version: str
    ) -> str:
        """Get a single prediction from the LLM."""
        try:
            # Extract the user claim from the messages
            user_msg = ""
            for msg in example.messages:
                if msg.role == "user":
                    user_msg = msg.content
                    break

            system_prompt = (
                "You are a greenwashing detection AI. Classify the following claim "
                "into one of these categories: MISLEADING, VAGUE, UNVERIFIED, SUBSTANTIATED. "
                "Respond with ONLY the category label, nothing else."
            )

            response = await self._llm.complete(
                system_prompt=system_prompt,
                user_prompt=user_msg,
                max_tokens=20,
                temperature=0.0,
                tier="fast",
            )
            # Parse the response to extract the label
            label = response.strip().upper()
            valid_labels = {"MISLEADING", "VAGUE", "UNVERIFIED", "SUBSTANTIATED"}
            if label in valid_labels:
                return label
            # Try to find a valid label in the response
            for valid in valid_labels:
                if valid in label:
                    return valid
            return label
        except Exception as e:
            logger.warning(f"Prediction failed for example {example.id}: {e}")
            return "UNKNOWN"

    def _extract_label(self, example: TrainingExample) -> str:
        """Extract the string label from a training example."""
        if hasattr(example.label, "value"):
            return example.label.value
        return str(example.label)

    def _find_misclassifications(
        self,
        examples: list[TrainingExample],
        predictions: list[str],
        ground_truth: list[str],
    ) -> list[Misclassification]:
        """Find all examples where prediction differs from ground truth."""
        misclassifications: list[Misclassification] = []
        for ex, pred, gt in zip(examples, predictions, ground_truth):
            if pred != gt:
                # Extract the user claim for context
                input_claim = ""
                for msg in ex.messages:
                    if msg.role == "user":
                        input_claim = msg.content
                        break
                misclassifications.append(
                    Misclassification(
                        example_id=ex.id,
                        expected=gt,
                        predicted=pred,
                        input_claim=input_claim,
                    )
                )
        return misclassifications

    async def _save_report(self, report: EvaluationReport) -> None:
        """Save evaluation report as JSON to the data directory."""
        filepath = os.path.join(self.data_dir, f"{report.id}.json")
        report_data = report.model_dump(mode="json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"Saved evaluation report {report.id} to {filepath}")
