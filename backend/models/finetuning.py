"""
Data models for the fine-tuning preparation subsystem.

Covers dataset splitting, balance validation, and Fireworks AI
fine-tuning configuration for the GreenLens greenwashing detector.

Enums and TrainingExample are reused from models.training — they are not
redefined here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.training import TrainingExample


class DatasetSplits(BaseModel):
    """Train / validation / test partitions of a labeled dataset."""

    train: list[TrainingExample]
    validation: list[TrainingExample]
    test: list[TrainingExample]


class BalanceResult(BaseModel):
    """
    Result of a severity-distribution balance check.

    `distribution` maps severity level -> fraction of the dataset (0.0 - 1.0).
    `violations` lists the severity levels exceeding the 40% threshold.
    """

    is_balanced: bool
    distribution: dict[str, float] = Field(default_factory=dict)
    violations: list[str] = Field(default_factory=list)


class FineTuneConfig(BaseModel):
    """Fireworks AI fine-tuning hyperparameter configuration."""

    base_model: str
    learning_rate: float = 2e-5
    epochs: int = 3
    batch_size: int = 4
    warmup_ratio: float = 0.1
    dataset_path: str = ""


class FineTuneDataset(BaseModel):
    """Paths to exported JSONL splits plus the generated fine-tune config."""

    train_path: str
    validation_path: str
    test_path: str
    total_examples: int
    config: FineTuneConfig
