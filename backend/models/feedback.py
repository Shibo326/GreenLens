"""Data models for the Feedback Learning subsystem."""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class UserCorrection(BaseModel):
    id: str = ""
    session_id: str
    user_id: str
    original_input: str
    ai_output: str
    correction_type: Literal["false_positive", "false_negative"]
    user_correction: str
    error_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CorrectionResult(BaseModel):
    correction_id: str
    status: Literal["logged", "conflict_detected", "consensus_reached"]
    consensus_count: int = 0
    conflict_with: str | None = None

class ConsensusResult(BaseModel):
    has_consensus: bool
    correction_count: int
    threshold: int = 3
    corrections: list[UserCorrection] = []

class ConflictCheckResult(BaseModel):
    has_conflict: bool
    conflicting_example_id: str | None = None
    conflicting_label: str | None = None
    requires_expert_review: bool = False
