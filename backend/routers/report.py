import io
import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from models.response import ReportRequest
from services.pdf_generator import PDFGenerator
from services.docx_generator import DOCXGenerator
from services.session_manager import SessionManager, SessionNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances (set from main.py at startup)
_pdf_generator: PDFGenerator | None = None
_docx_generator: DOCXGenerator | None = None
_session_manager: SessionManager | None = None


def _err(status: int, message: str, code: str, suggestion: str = ""):
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


class ReportRequestWithFormat(ReportRequest):
    """Extended report request supporting format selection."""
    format: Literal["pdf", "docx"] = "pdf"


@router.post("/report")
async def generate_report(request: ReportRequestWithFormat):
    """
    Generate and return a report for a completed analysis session.

    Supports both PDF and DOCX formats via the `format` field.
    - format: "pdf" (default) returns application/pdf
    - format: "docx" returns application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    pdf_generator = _pdf_generator
    docx_generator = _docx_generator
    session_manager = _session_manager

    if session_manager is None or pdf_generator is None:
        return _err(503, "Service is starting up. Please try again in a moment.", "SERVICE_UNAVAILABLE", "The server is still initializing. Please retry in 10-20 seconds.")

    session_id = request.sessionId
    export_format = request.format

    # --- Validate session with completed analysis ---
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        return _err(404, "Session not found.", "SESSION_NOT_FOUND", "Please upload documents and run analysis first.")

    if session.analysis is None:
        return _err(404, "No analysis available to export.", "NO_ANALYSIS", "Please run the analysis before generating a report.")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # --- Generate report based on format ---
    if export_format == "docx":
        try:
            docx_bytes = docx_generator.generate_report(
                analysis=session.analysis,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"DOCX generation failed for session {session_id}: {e}")
            return _err(500, "Report generation failed.", "PDF_GENERATION_FAILED", "An error occurred generating the DOCX report. Please try again.")

        filename = f"greenlens-report-{today}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(docx_bytes)),
            },
        )
    else:
        # Default: PDF
        try:
            pdf_bytes = pdf_generator.generate_report(
                analysis=session.analysis,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"PDF generation failed for session {session_id}: {e}")
            return _err(500, "Report generation failed.", "PDF_GENERATION_FAILED", "An error occurred generating the PDF report. Please try again.")

        filename = f"greenlens-report-{today}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
