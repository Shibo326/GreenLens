import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from models.document import Chunk, ProcessingStatus, UploadedDocument
from models.response import UploadResponse
from services.document_parser import DocumentParser, ExtractionError
from services.embedding_service import EmbeddingService
from services.session_manager import SessionManager, SessionNotFoundError
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ---- Dependency instances (injected via app state in main.py) ----
_document_parser: DocumentParser | None = None
_embedding_service: EmbeddingService | None = None
_vector_store: VectorStore | None = None
_session_manager: SessionManager | None = None

# Constants
MAX_FILE_COUNT = 3
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ACCEPTED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# MIME → fileType mapping
MIME_TO_FILE_TYPE = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
}


def _err(status: int, message: str, code: str, suggestion: str = ""):
    """Return a structured JSONResponse matching ErrorResponse schema."""
    return JSONResponse(
        status_code=status,
        content={"error": message, "code": code, "suggestion": suggestion or None},
    )


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
):
    """
    Upload one or more documents for analysis.

    Accepts PDF, PNG, and JPEG files.
    Returns a session ID and per-document processing status.
    """
    document_parser = _document_parser
    embedding_service = _embedding_service
    vector_store = _vector_store
    session_manager = _session_manager

    # Service readiness check
    if document_parser is None or embedding_service is None or vector_store is None or session_manager is None:
        return _err(503, "Service is starting up. Please try again in a moment.", "SERVICE_UNAVAILABLE", "The server is still initializing. Please retry in 10-20 seconds.")

    # --- Validate file count ---
    if len(files) == 0:
        return _err(400, "At least one file is required.", "TOO_MANY_FILES", "Please select at least one file to upload.")
    if len(files) > MAX_FILE_COUNT:
        return _err(400, "You can upload up to 3 files at a time.", "TOO_MANY_FILES", "Please reduce to 3 or fewer files per upload.")

    session_id = str(uuid.uuid4())
    uploaded_documents: list[UploadedDocument] = []
    all_chunks: list[Chunk] = []

    # --- Process each file ---
    for upload_file in files:
        file_bytes = await upload_file.read()
        filename = upload_file.filename or "unknown"
        content_type = upload_file.content_type or ""

        # Normalize content-type — strip charset etc.
        mime_type = content_type.split(";")[0].strip().lower()

        # If MIME type is missing or generic, infer from filename extension
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if mime_type not in ACCEPTED_MIME_TYPES:
            ext_to_mime = {
                "pdf": "application/pdf",
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
            if ext in ext_to_mime:
                mime_type = ext_to_mime[ext]
                logger.info(f"Inferred MIME type '{mime_type}' from extension for {filename}")

        doc_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow()
        file_size = len(file_bytes)
        file_type = MIME_TO_FILE_TYPE.get(mime_type, "pdf")

        # --- Validate MIME type ---
        if mime_type not in ACCEPTED_MIME_TYPES:
            return _err(
                400,
                f"Unsupported file format: {mime_type}. Accepted formats: PDF, PNG, JPEG, DOCX.",
                "INVALID_FILE_TYPE",
                "Please upload PDF, PNG, JPG, JPEG, or DOCX files only.",
            )

        # --- Validate file size ---
        if file_size > MAX_FILE_SIZE:
            return _err(400, "This file exceeds the 10 MB limit.", "FILE_TOO_LARGE", "Please reduce the file size to under 10 MB.")

        # --- Process file ---
        try:
            # 1. Extract text
            text = document_parser.extract_text(file_bytes, mime_type)

            # 2. Chunk text
            chunk_texts = embedding_service.chunk_text(text)
            if not chunk_texts:
                chunk_texts = [text[:1000]] if text.strip() else []

            # 3. Generate embeddings in batch
            embeddings = embedding_service.embed_batch(chunk_texts)

            # 4. Build Chunk objects
            doc_chunks = []
            for idx, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk = Chunk(
                    id=str(uuid.uuid4()),
                    text=chunk_text,
                    embedding=embedding,
                    source_document=filename,
                    document_type=file_type,
                    chunk_index=idx,
                )
                doc_chunks.append(chunk)

            all_chunks.extend(doc_chunks)

            doc = UploadedDocument(
                id=doc_id,
                filename=filename,
                fileType=file_type,
                fileSize=file_size,
                uploadedAt=uploaded_at,
                processingStatus=ProcessingStatus.COMPLETED,
            )
            uploaded_documents.append(doc)
            logger.info(f"Processed {filename}: {len(doc_chunks)} chunks")

        except ExtractionError as e:
            logger.warning(f"Extraction failed for {filename}: {e}")
            doc = UploadedDocument(
                id=doc_id,
                filename=filename,
                fileType=file_type,
                fileSize=file_size,
                uploadedAt=uploaded_at,
                processingStatus=ProcessingStatus.FAILED,
            )
            uploaded_documents.append(doc)
        except Exception as e:
            logger.error(f"Unexpected error processing {filename}: {e}")
            doc = UploadedDocument(
                id=doc_id,
                filename=filename,
                fileType=file_type,
                fileSize=file_size,
                uploadedAt=uploaded_at,
                processingStatus=ProcessingStatus.FAILED,
            )
            uploaded_documents.append(doc)

    # --- Check if all files failed ---
    successful = [d for d in uploaded_documents if d.processingStatus == ProcessingStatus.COMPLETED]
    if not successful:
        return _err(422, "All documents failed to process.", "UPLOAD_FAILED", "Check that files are valid and not corrupted, then try again.")

    # --- Store chunks in vector store ---
    if all_chunks:
        vector_store.add_chunks(session_id, all_chunks)

    # --- Create session ---
    session_manager.create_session(session_id, uploaded_documents)

    response = UploadResponse(
        sessionId=session_id,
        documents=uploaded_documents,
        message=f"Successfully processed {len(successful)} of {len(files)} document(s).",
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@router.get("/session/{session_id}/check")
async def check_session(session_id: str):
    """
    Lightweight health check — returns 200 if session exists, 404 if not.
    Used by the frontend on startup to detect stale localStorage sessions.
    """
    session_manager = _session_manager
    try:
        session_manager.get_session(session_id)
        return JSONResponse(content={"valid": True})
    except SessionNotFoundError:
        return JSONResponse(status_code=404, content={"valid": False, "error": "Session not found.", "code": "SESSION_NOT_FOUND", "suggestion": "Please upload new documents to start a fresh session."})


@router.post("/session/new")
async def new_session():
    """
    Create a fresh empty session and return its ID.
    The client uses this to reset state without uploading new files —
    e.g. when the user clicks "New Session" in the chat UI.
    """
    session_manager = _session_manager
    session_id = str(uuid.uuid4())
    session_manager.create_session(session_id, documents=[])
    logger.info(f"New empty session created: {session_id}")
    return JSONResponse(content={"sessionId": session_id})
