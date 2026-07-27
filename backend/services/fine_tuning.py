"""
FineTuningService -- prepares datasets and configurations for Fireworks AI fine-tuning.

Handles exporting ground truth datasets as JSONL splits, validating severity
distribution balance, generating fine-tuning configs, and performing stratified
dataset splitting.
"""
import json
import logging
import os
import random
from collections import defaultdict

from models.finetuning import (
    BalanceResult,
    DatasetSplits,
    FineTuneConfig,
    FineTuneDataset,
)
from models.training import SeverityLevel, TrainingExample

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "finetuning")


class FineTuningService:
    def __init__(self, data_dir: str | None = None, training_pipeline=None):
        self.data_dir = data_dir or _DATA_DIR
        self.training_pipeline = training_pipeline
        os.makedirs(self.data_dir, exist_ok=True)

    async def export_dataset(self) -> FineTuneDataset:
        """Export ground truth dataset from TrainingPipelineService as train/val/test JSONL splits."""
        if not self.training_pipeline:
            raise ValueError("TrainingPipelineService is required for dataset export")

        examples = await self.training_pipeline.get_examples(limit=10000)
        if not examples:
            raise ValueError("No training examples available for export")

        splits = self.split_dataset(examples)

        train_path = os.path.join(self.data_dir, "train.jsonl")
        val_path = os.path.join(self.data_dir, "validation.jsonl")
        test_path = os.path.join(self.data_dir, "test.jsonl")

        self._write_jsonl(splits.train, train_path)
        self._write_jsonl(splits.validation, val_path)
        self._write_jsonl(splits.test, test_path)

        config = await self.generate_config("accounts/fireworks/models/llama-v3p1-8b-instruct")
        config.dataset_path = train_path

        total = len(splits.train) + len(splits.validation) + len(splits.test)
        logger.info(
            f"Exported fine-tuning dataset: {len(splits.train)} train, "
            f"{len(splits.validation)} val, {len(splits.test)} test"
        )

        return FineTuneDataset(
            train_path=train_path,
            validation_path=val_path,
            test_path=test_path,
            total_examples=total,
            config=config,
        )

    async def validate_balance(self, dataset: list[TrainingExample]) -> BalanceResult:
        """Check severity distribution, flag if any category > 40%."""
        if not dataset:
            return BalanceResult(is_balanced=True, distribution={}, violations=[])

        severity_counts: dict[str, int] = defaultdict(int)
        for example in dataset:
            key = example.severity.value if isinstance(example.severity, SeverityLevel) else str(example.severity)
            severity_counts[key] += 1

        total = len(dataset)
        distribution: dict[str, float] = {
            level: count / total for level, count in severity_counts.items()
        }

        violations = [
            level for level, fraction in distribution.items() if fraction > 0.4
        ]

        return BalanceResult(
            is_balanced=len(violations) == 0,
            distribution=distribution,
            violations=violations,
        )

    async def generate_config(self, base_model: str) -> FineTuneConfig:
        """Return a FineTuneConfig with default hyperparameters for Fireworks AI."""
        return FineTuneConfig(
            base_model=base_model,
            learning_rate=2e-5,
            epochs=3,
            batch_size=4,
            warmup_ratio=0.1,
            dataset_path=os.path.join(self.data_dir, "train.jsonl"),
        )

    def split_dataset(
        self,
        examples: list[TrainingExample],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
    ) -> DatasetSplits:
        """Stratified split by severity level into train/val/test sets.

        Ensures each severity level appears in all 3 splits (as long as there
        are enough examples per level — at least 3).
        """
        # Group examples by severity level
        by_severity: dict[str, list[TrainingExample]] = defaultdict(list)
        for example in examples:
            key = example.severity.value if isinstance(example.severity, SeverityLevel) else str(example.severity)
            by_severity[key].append(example)

        train: list[TrainingExample] = []
        validation: list[TrainingExample] = []
        test: list[TrainingExample] = []

        for severity_level, group in by_severity.items():
            # Shuffle within each severity group for randomness
            shuffled = list(group)
            random.shuffle(shuffled)

            n = len(shuffled)
            if n >= 3:
                # Enough examples to guarantee representation in all splits
                n_train = max(1, round(n * train_ratio))
                n_val = max(1, round(n * val_ratio))
                n_test = max(1, n - n_train - n_val)

                # Adjust if we over-allocated
                if n_train + n_val + n_test > n:
                    n_train = n - n_val - n_test

                train.extend(shuffled[:n_train])
                validation.extend(shuffled[n_train:n_train + n_val])
                test.extend(shuffled[n_train + n_val:])
            elif n == 2:
                # Put one in train, one in validation (can't guarantee test)
                train.append(shuffled[0])
                validation.append(shuffled[1])
            elif n == 1:
                # Only one example — put it in train
                train.append(shuffled[0])

        return DatasetSplits(train=train, validation=validation, test=test)

    def _write_jsonl(self, examples: list[TrainingExample], path: str) -> None:
        """Write examples as JSONL where each line is {"messages": [...]} in Fireworks format."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for example in examples:
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in example.messages
                ]
                line = json.dumps({"messages": messages}, ensure_ascii=False)
                f.write(line + "\n")
