"""
Data models for the AI Advanced Training subsystem.

Covers training data curation, validation, and dataset statistics
for the GreenLens greenwashing detection pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GreenwashVerdict(str, Enum):
    """Verdict label for a greenwashing claim."""

    MISLEADING = "MISLEADING"
    VAGUE = "VAGUE"
    UNVERIFIED = "UNVERIFIED"
    SUBSTANTIATED = "SUBSTANTIATED"


class SeverityLevel(str, Enum):
    """Severity classification for greenwashing findings."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExampleSource(str, Enum):
    """Provenance tag indicating how a training example was sourced."""

    EXPERT = "expert"
    FEEDBACK = "feedback"


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Single message in Fireworks AI chat-completion format."""

    role: Literal["system", "user", "assistant"]
    content: str


class TrainingExample(BaseModel):
    """A labeled training example in chat-completion format."""

    id: str = Field(default_factory=lambda: "")
    messages: list[ChatMessage] = Field(min_length=3)
    label: GreenwashVerdict
    severity: SeverityLevel
    sector: str
    company: str
    source: ExampleSource = ExampleSource.EXPERT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation and statistics models
# ---------------------------------------------------------------------------


class ValidationResult(BaseModel):
    """Result of schema validation for a training example."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


class DatasetStats(BaseModel):
    """Summary statistics for the training dataset."""

    total_examples: int
    by_label: dict[str, int]
    by_severity: dict[str, int]
    by_sector: dict[str, int]
    by_source: dict[str, int]
    evaluation_ready: bool
    finetune_ready: bool
