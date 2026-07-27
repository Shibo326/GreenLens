"""
Data models for the Knowledge Base subsystem.

Covers regulatory documents, enforcement actions, retrieved precedents,
and knowledge base statistics for the GreenLens greenwashing detection pipeline.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------


class RegulatoryDocument(BaseModel):
    """A regulatory document stored in the knowledge base.

    Represents legislation, guidelines, or standards related to
    environmental marketing claims (e.g., FTC Green Guides, EU Green Claims Directive).
    """

    id: str = ""
    title: str
    jurisdiction: str
    document_type: str
    content: str
    effective_date: datetime | None = None
    url: str = ""


class EnforcementAction(BaseModel):
    """A greenwashing enforcement action taken by a regulatory body.

    Records fines, rulings, and outcomes against companies found
    to have made misleading environmental claims.
    """

    id: str = ""
    company_name: str
    violation_type: str
    fine_amount: float | None = None
    fine_currency: str = "USD"
    ruling_date: datetime
    jurisdiction: str
    summary: str
    source_url: str = ""


# ---------------------------------------------------------------------------
# Retrieval models
# ---------------------------------------------------------------------------


class RetrievedPrecedent(BaseModel):
    """A precedent retrieved from the knowledge base for a given claim.

    Contains the relevant excerpt, its source jurisdiction, and an optional
    linked enforcement action for additional context.
    """

    document_title: str
    jurisdiction: str
    excerpt: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    enforcement_action: EnforcementAction | None = None


# ---------------------------------------------------------------------------
# Statistics models
# ---------------------------------------------------------------------------


class KnowledgeBaseStats(BaseModel):
    """Summary statistics for the knowledge base contents."""

    regulatory_documents: int
    enforcement_actions: int
    by_jurisdiction: dict[str, int] = Field(default_factory=dict)
