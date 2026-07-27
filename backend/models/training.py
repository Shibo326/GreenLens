"""
Data models for the training pipeline of the AI Advanced Training subsystem.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class GreenwashVerdict(str, Enum):
    MISLEADING = "MISLEADING"
    VAGUE = "VAGUE"
    UNVERIFIED = "UNVERIFIED"
    SUBSTANTIATED = "SUBSTANTIATED"


class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExampleSource(str, Enum):
    EXPERT = "expert"
    FEEDBACK = "feedback"


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class TrainingExample(BaseModel):
    id: str = Field(default_factory=lambda: "")
    messages: list[ChatMessage] = Field(min_length=3)
    label: GreenwashVerdict
    severity: SeverityLevel
    sector: str
    company: str
    source: ExampleSource = ExampleSource.EXPERT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class DatasetStats(BaseModel):
    total_examples: int
    by_label: dict[str, int]
    by_severity: dict[str, int]
    by_sector: dict[str, int]
    by_source: dict[str, int]
    evaluation_ready: bool
    finetune_ready: bool
