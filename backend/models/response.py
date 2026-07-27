"""
Request/response envelope models for the DealFlow AI backend.

All field names exactly match the frontend's `lib/types.ts` and `lib/api.ts`
contracts so that JSON serialization requires no aliasing.

Datetime fields use ConfigDict(json_encoders=...) so that `model_dump(mode="json")`
produces ISO 8601 strings — matching what the frontend does with `new Date(isoString)`.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from models.document import UploadedDocument


# ---------------------------------------------------------------------------
# Nested helper models
# ---------------------------------------------------------------------------


class SourceLink(BaseModel):
    """A web source link discovered during real-time research.
    Matches TS interface SourceLink in lib/types.ts.
    """

    title: str
    url: str
    snippet: str = ""


class DocumentExcerpt(BaseModel):
    """Embedded in Conflict.documentA / documentB.
    Matches TS: { name: string; excerpt: string }
    """

    name: str
    excerpt: str


# ---------------------------------------------------------------------------
# Analysis sub-models
# ---------------------------------------------------------------------------


class Risk(BaseModel):
    """Individual risk item.
    Matches TS interface Risk in lib/types.ts.
    """

    id: str
    level: Literal["HIGH", "MEDIUM", "LOW"]
    description: str
    sourceDocument: str
    category: str


class Conflict(BaseModel):
    """Cross-document contradiction detected by the conflict engine.
    Matches TS interface Conflict in lib/types.ts.
    """

    id: str
    type: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    documentA: DocumentExcerpt  # {"name": str, "excerpt": str}
    documentB: DocumentExcerpt  # {"name": str, "excerpt": str}
    explanation: str
    recommendedAction: str


class ComparisonRow(BaseModel):
    """One row of the supplier/document comparison matrix.
    Matches TS interface ComparisonRow in lib/types.ts.
    """

    field: str
    values: dict[str, str]  # {document_name: value_string}
    winner: str | None = None


class Recommendation(BaseModel):
    """Final procurement recommendation.
    Matches TS interface Recommendation in lib/types.ts.
    """

    title: str
    summary: str
    nextSteps: list[str]
    confidence: float  # 0.0 – 1.0


class AnalysisResult(BaseModel):
    """Complete structured output of the AI analysis pipeline.
    Matches TS interface AnalysisResult in lib/types.ts.
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    analyzedAt: datetime  # serialized as ISO 8601
    executiveSummary: str
    greenwashScore: int | None = None  # 0-100, None if not yet computed
    risks: list[Risk]
    comparisonMatrix: list[ComparisonRow]
    conflicts: list[Conflict]
    recommendation: Recommendation
    suggestedQuestions: list[str] = []
    sources: list[SourceLink] = []  # Web sources used during analysis


# ---------------------------------------------------------------------------
# Chat sub-models
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    """A single grounded evidence citation from the RAG retrieval.
    Matches TS interface Evidence in lib/types.ts.
    """

    quote: str  # max 200 chars (enforced in router)
    sourceDocument: str
    documentType: Literal["pdf", "image", "document"]


class StructuredAIResponse(BaseModel):
    """The structured payload returned by the /api/chat endpoint.
    Matches TS interface StructuredAIResponse in lib/types.ts.
    """

    answer: str
    evidence: list[Evidence]
    risks: str
    recommendation: str


# ---------------------------------------------------------------------------
# Request / Response envelope models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response body for POST /api/upload.
    Matches TS interface UploadResponse in lib/api.ts.
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    sessionId: str
    documents: list[UploadedDocument]
    message: str


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/analyze."""

    sessionId: str
    force: bool = False


class AnalyzeResponse(BaseModel):
    """Response body for POST /api/analyze.
    Matches TS interface AnalyzeResponse in lib/api.ts.
    Optional `estimatedTimeSeconds` aligns with the frontend's optional field.
    """

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    sessionId: str
    status: Literal["processing", "completed"]
    analysis: AnalysisResult | None = None
    estimatedTimeSeconds: int | None = None


class ChatHistoryMessage(BaseModel):
    """A single message in the chat history for multi-turn context."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    sessionId: str
    question: str
    history: list[ChatHistoryMessage] = []
    simplify: bool = False  # ELI15 mode — simplified language output


class ChatResponse(BaseModel):
    """Response body for POST /api/chat.
    Matches TS interface ChatResponse in lib/api.ts.
    """

    messageId: str
    role: Literal["assistant"]
    structuredResponse: StructuredAIResponse
    processingTimeMs: int


class ReportRequest(BaseModel):
    """Request body for POST /api/report."""

    sessionId: str
    includeChat: bool = False


class ErrorResponse(BaseModel):
    """Uniform error envelope for all 4xx/5xx responses.
    Matches TS interface ErrorResponse in lib/api.ts.

    Valid `code` values mirror the frontend's API_ERROR_CODES:
      FILE_SIZE_EXCEEDED, FILE_COUNT_EXCEEDED, UNSUPPORTED_FORMAT,
      UPLOAD_FAILED, ANALYSIS_FAILED, SESSION_NOT_FOUND,
      NETWORK_ERROR, UNAUTHORIZED, UNKNOWN_ERROR, INVALID_REQUEST,
      REPORT_FAILED
    """

    error: str
    code: str
    details: dict | None = None


# ---------------------------------------------------------------------------
# Quick Scan models
# ---------------------------------------------------------------------------


class QuickScanRequest(BaseModel):
    """Request body for POST /api/quick-scan."""

    claim: str


class QuickScanResponse(BaseModel):
    """Response body for POST /api/quick-scan — instant single-claim verdict."""

    verdict: str
    whatToLookFor: list[str]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
