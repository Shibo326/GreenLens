"""
Knowledge Base Service for GreenLens AI Advanced Training.

Manages the regulatory and precedent knowledge base using a dedicated
ChromaDB collection ("knowledge_base") separate from document uploads.
"""

from __future__ import annotations

import logging
import os
from uuid import uuid4

from models.knowledge_base import (
    EnforcementAction,
    KnowledgeBaseStats,
    RegulatoryDocument,
    RetrievedPrecedent,
)

logger = logging.getLogger(__name__)

# ChromaDB persistent directory — same base as vector_store.py
_DEFAULT_CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", _DEFAULT_CHROMA_DIR)

_COLLECTION_NAME = "knowledge_base"

_shared_client = None


def _get_client():
    """Get or create a shared ChromaDB PersistentClient."""
    global _shared_client
    if _shared_client is None:
        import chromadb

        os.makedirs(_CHROMA_DIR, exist_ok=True)
        _shared_client = chromadb.PersistentClient(path=_CHROMA_DIR)
        logger.info(f"KnowledgeBase ChromaDB client initialized at {_CHROMA_DIR}")
    return _shared_client


def reset_client():
    """Reset the shared client (used in tests to get a fresh isolated client)."""
    global _shared_client
    _shared_client = None


class KnowledgeBaseService:
    """
    Manages the regulatory and precedent knowledge base.

    Uses a ChromaDB collection named "knowledge_base" to store regulatory
    documents and enforcement actions, enabling precedent retrieval for
    greenwashing claim analysis.
    """

    def __init__(self):
        self._embedding_service = None
        self._collection = None
        try:
            from services.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService()
        except Exception as e:
            logger.warning(
                f"EmbeddingService unavailable, knowledge base will be limited: {e}"
            )

        try:
            client = _get_client()
            self._collection = client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"description": "GreenLens regulatory knowledge base"},
            )
            logger.info(f"Knowledge base collection '{_COLLECTION_NAME}' ready")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable, knowledge base disabled: {e}")

    async def add_regulatory_document(self, doc: RegulatoryDocument) -> str:
        """
        Chunk, embed, and store a regulatory document in the knowledge base.

        Args:
            doc: The regulatory document to add.

        Returns:
            The document ID (generated if not provided).
        """
        doc_id = doc.id if doc.id else str(uuid4())

        if self._collection is None or self._embedding_service is None:
            logger.error("Knowledge base not available (ChromaDB or embeddings missing)")
            return doc_id

        # Chunk the document content
        chunks = self._embedding_service.chunk_text(doc.content)
        if not chunks:
            logger.warning(f"No chunks produced for document '{doc.title}'")
            return doc_id

        # Embed all chunks
        embeddings = self._embedding_service.embed_batch(chunks)

        # Prepare IDs and metadata for each chunk
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "title": doc.title,
                "jurisdiction": doc.jurisdiction,
                "document_type": doc.document_type,
                "chunk_index": i,
                "type": "regulatory_document",
                "effective_date": doc.effective_date.isoformat() if doc.effective_date else "",
                "url": doc.url,
            }
            for i in range(len(chunks))
        ]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        logger.info(
            f"Added regulatory document '{doc.title}' ({len(chunks)} chunks) "
            f"with ID {doc_id}"
        )
        return doc_id

    async def add_enforcement_action(self, action: EnforcementAction) -> str:
        """
        Store an enforcement action as a document in the knowledge base.

        Args:
            action: The enforcement action to add.

        Returns:
            The action ID (generated if not provided).
        """
        action_id = action.id if action.id else str(uuid4())

        if self._collection is None or self._embedding_service is None:
            logger.error("Knowledge base not available (ChromaDB or embeddings missing)")
            return action_id

        # Build a text representation of the enforcement action for embedding
        text = (
            f"Enforcement Action: {action.company_name}. "
            f"Violation: {action.violation_type}. "
            f"Jurisdiction: {action.jurisdiction}. "
            f"Ruling date: {action.ruling_date.isoformat()}. "
            f"Summary: {action.summary}"
        )
        if action.fine_amount is not None:
            text += f" Fine: {action.fine_amount} {action.fine_currency}."

        # Embed the action text
        embedding = self._embedding_service.embed(text)

        metadata = {
            "doc_id": action_id,
            "title": f"Enforcement: {action.company_name} - {action.violation_type}",
            "jurisdiction": action.jurisdiction,
            "document_type": "enforcement_action",
            "type": "enforcement_action",
            "company_name": action.company_name,
            "violation_type": action.violation_type,
            "fine_amount": action.fine_amount if action.fine_amount is not None else -1.0,
            "fine_currency": action.fine_currency,
            "ruling_date": action.ruling_date.isoformat(),
            "source_url": action.source_url,
        }

        self._collection.add(
            ids=[action_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

        logger.info(
            f"Added enforcement action for '{action.company_name}' "
            f"({action.violation_type}) with ID {action_id}"
        )
        return action_id

    async def query_precedents(
        self,
        claim_text: str,
        jurisdiction: str | None = None,
        k: int = 3,
    ) -> list[RetrievedPrecedent]:
        """
        Query the knowledge base for relevant precedents matching a claim.

        Args:
            claim_text: The claim text to find precedents for.
            jurisdiction: Optional jurisdiction filter.
            k: Number of results to return.

        Returns:
            List of retrieved precedents ordered by relevance.
        """
        if self._collection is None or self._embedding_service is None:
            logger.warning("Knowledge base not available for querying")
            return []

        # Check if collection has any documents
        count = self._collection.count()
        if count == 0:
            return []

        # Embed the query
        query_embedding = self._embedding_service.embed(claim_text)

        # Build where filter for jurisdiction if provided
        where_filter = None
        if jurisdiction:
            where_filter = {"jurisdiction": jurisdiction}

        actual_k = min(k, count)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        precedents: list[RetrievedPrecedent] = []

        if not results["ids"] or not results["ids"][0]:
            return precedents

        for i, _id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            document_text = results["documents"][0][i]
            distance = results["distances"][0][i] if results.get("distances") else 1.0

            # Convert cosine distance to a relevance score (0-1, higher is better)
            relevance_score = max(0.0, min(1.0, 1.0 - distance))

            # Build enforcement action if this is one
            enforcement = None
            if metadata.get("type") == "enforcement_action":
                fine_amount = metadata.get("fine_amount")
                if fine_amount == -1.0:
                    fine_amount = None

                ruling_date_str = metadata.get("ruling_date", "")
                try:
                    from datetime import datetime

                    ruling_date = datetime.fromisoformat(ruling_date_str)
                except (ValueError, TypeError):
                    from datetime import datetime

                    ruling_date = datetime.utcnow()

                enforcement = EnforcementAction(
                    id=metadata.get("doc_id", _id),
                    company_name=metadata.get("company_name", ""),
                    violation_type=metadata.get("violation_type", ""),
                    fine_amount=fine_amount,
                    fine_currency=metadata.get("fine_currency", "USD"),
                    ruling_date=ruling_date,
                    jurisdiction=metadata.get("jurisdiction", ""),
                    summary=document_text,
                    source_url=metadata.get("source_url", ""),
                )

            precedent = RetrievedPrecedent(
                document_title=metadata.get("title", "Unknown"),
                jurisdiction=metadata.get("jurisdiction", "Unknown"),
                excerpt=document_text,
                relevance_score=relevance_score,
                enforcement_action=enforcement,
            )
            precedents.append(precedent)

        return precedents

    async def get_stats(self) -> KnowledgeBaseStats:
        """
        Return document counts by type and jurisdiction.

        Returns:
            KnowledgeBaseStats with counts of regulatory documents,
            enforcement actions, and breakdown by jurisdiction.
        """
        if self._collection is None:
            return KnowledgeBaseStats(
                regulatory_documents=0,
                enforcement_actions=0,
                by_jurisdiction={},
            )

        count = self._collection.count()
        if count == 0:
            return KnowledgeBaseStats(
                regulatory_documents=0,
                enforcement_actions=0,
                by_jurisdiction={},
            )

        # Retrieve all metadata to compute stats
        results = self._collection.get(include=["metadatas"], limit=count)

        regulatory_count = 0
        enforcement_count = 0
        by_jurisdiction: dict[str, int] = {}

        # Track unique doc_ids for regulatory documents to avoid
        # counting each chunk separately
        seen_regulatory_ids: set[str] = set()

        if results["metadatas"]:
            for metadata in results["metadatas"]:
                doc_type = metadata.get("type", "")
                jurisdiction = metadata.get("jurisdiction", "Unknown")

                if doc_type == "enforcement_action":
                    enforcement_count += 1
                    by_jurisdiction[jurisdiction] = (
                        by_jurisdiction.get(jurisdiction, 0) + 1
                    )
                elif doc_type == "regulatory_document":
                    doc_id = metadata.get("doc_id", "")
                    if doc_id and doc_id not in seen_regulatory_ids:
                        seen_regulatory_ids.add(doc_id)
                        regulatory_count += 1
                        by_jurisdiction[jurisdiction] = (
                            by_jurisdiction.get(jurisdiction, 0) + 1
                        )

        return KnowledgeBaseStats(
            regulatory_documents=regulatory_count,
            enforcement_actions=enforcement_count,
            by_jurisdiction=by_jurisdiction,
        )
