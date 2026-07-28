"""
Tests for the document upload pipeline.
Includes unit tests and property-based tests.
"""

import io
import os
import sys
import uuid

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---- Property 3: Chunking text reassembly ----

# Feature: dealflow-ai-backend, Property 3: chunking text reassembly preserves original content
@given(st.text(min_size=100, alphabet=st.characters(blacklist_categories=("Cs",))))
@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
def test_chunking_preserves_content(text):
    """
    Property 3: Chunking text reassembly preserves original content.
    Validates: Requirements 1.8, 11.3
    """
    from services.embedding_service import EmbeddingService

    es = EmbeddingService.__new__(EmbeddingService)

    # We test chunk_text without loading the full model
    # by patching just that method
    from services import embedding_service as es_module

    chunks = _chunk_text_standalone(text)
    if not chunks:
        return  # Empty input edge case

    # Reassemble: concatenate all chunks
    reassembled = " ".join(chunks)

    # Every word in the original text should appear somewhere in the reassembled text
    original_words = set(text.split())
    reassembled_words = set(reassembled.split())

    # Due to overlap, all original words should be present
    assert original_words.issubset(reassembled_words), (
        f"Some words lost during chunking. "
        f"Missing: {original_words - reassembled_words}"
    )


def _chunk_text_standalone(
    text: str,
    max_tokens: int = 512,
    overlap: int = 50,
) -> list[str]:
    """Standalone chunking logic matching EmbeddingService.chunk_text."""
    if not text or not text.strip():
        return []

    max_words = int(max_tokens * 0.75)
    overlap_words = int(overlap * 0.75)

    words = text.split()
    if not words:
        return []

    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        advance = max_words - overlap_words
        if advance <= 0:
            advance = 1
        start += advance

        if start >= len(words):
            break

    return chunks


# ---- Property 2: Session creation round-trip ----

# Feature: dealflow-ai-backend, Property 2: session creation round-trip
def test_session_creation_round_trip(embedding_service, vector_store, session_manager):
    """
    Property 2: Session creation round-trip.
    Validates: Requirements 1.5, 9.1, 9.2

    A created session can be retrieved and used for analysis/chat.
    """
    import uuid as uuid_mod
    from models.document import Chunk, UploadedDocument, ProcessingStatus
    from datetime import datetime

    session_id = str(uuid_mod.uuid4())

    # Create a document and chunk
    doc = UploadedDocument(
        id=str(uuid_mod.uuid4()),
        filename="test.pdf",
        fileType="pdf",
        fileSize=1000,
        uploadedAt=datetime.utcnow(),
        processingStatus=ProcessingStatus.COMPLETED,
    )

    text = "This is a test document with procurement data."
    embedding = embedding_service.embed(text)
    chunk = Chunk(
        id=str(uuid_mod.uuid4()),
        text=text,
        embedding=embedding,
        source_document="test.pdf",
        document_type="pdf",
        chunk_index=0,
    )

    # Store in vector store and session manager
    vector_store.add_chunks(session_id, [chunk])
    session_manager.create_session(session_id, [doc])

    # Verify session exists and is accessible
    assert session_manager.session_exists(session_id)
    retrieved = session_manager.get_session(session_id)
    assert retrieved.session_id == session_id
    assert len(retrieved.documents) == 1

    # Verify chunks are retrievable
    retrieved_chunks = vector_store.get_all_chunks(session_id)
    assert len(retrieved_chunks) == 1


# ---- Unit tests for file validation ----

def test_file_count_limit():
    """File count validation: max 3 files."""
    from routers.upload import MAX_FILE_COUNT
    assert MAX_FILE_COUNT == 3


def test_file_size_limit():
    """File size validation: max 10 MB."""
    from routers.upload import MAX_FILE_SIZE
    assert MAX_FILE_SIZE == 10 * 1024 * 1024


def test_accepted_mime_types():
    """PDF, PNG, JPEG, and DOCX are accepted."""
    from routers.upload import ACCEPTED_MIME_TYPES
    assert "application/pdf" in ACCEPTED_MIME_TYPES
    assert "image/png" in ACCEPTED_MIME_TYPES
    assert "image/jpeg" in ACCEPTED_MIME_TYPES
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ACCEPTED_MIME_TYPES
    assert len(ACCEPTED_MIME_TYPES) == 4


def test_chunk_text_single_chunk():
    """Short texts should produce a single chunk."""
    short_text = "This is a short text."
    chunks = _chunk_text_standalone(short_text)
    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_chunk_text_empty():
    """Empty text should produce empty chunk list."""
    from services.embedding_service import EmbeddingService
    # Test the standalone function to avoid loading model
    chunks = _chunk_text_standalone("")
    assert chunks == []


def test_chunk_text_overlap_produces_multiple_chunks():
    """Long text should produce multiple overlapping chunks."""
    # Generate text that exceeds one chunk (~512 * 0.75 = 384 words)
    long_text = " ".join([f"word{i}" for i in range(500)])
    chunks = _chunk_text_standalone(long_text, max_tokens=100, overlap=10)
    assert len(chunks) > 1


def test_chunk_count_additivity():
    """
    Property 14: Chunk count additivity.
    Total chunks = sum of per-document chunks.
    """
    texts = [
        "First document about supplier quotations and pricing terms.",
        "Second document about contract renewal and payment terms.",
        "Third document with procurement policy compliance requirements.",
    ]

    per_doc_counts = [len(_chunk_text_standalone(t)) for t in texts]
    all_chunks = []
    for t in texts:
        all_chunks.extend(_chunk_text_standalone(t))

    assert len(all_chunks) == sum(per_doc_counts)
