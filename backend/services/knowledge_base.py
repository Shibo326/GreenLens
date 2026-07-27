"""
KnowledgeBaseService — manages the regulatory and precedent knowledge base
that grounds RAG responses for greenwashing detection.

Storage layout:
- ChromaDB collection "knowledge_base" holds embedded chunks for retrieval.
  Chunk metadata always carries `jurisdiction` and `document_type` so queries
  can be filtered by jurisdiction. This collection is kept separate from the
  per-session document-upload collections created by VectorStore.
- JSON files under backend/data/knowledge_base/ hold the full structured
  records (regulatory documents and enforcement actions) so precedents can be
  rehydrated into Pydantic models after retrieval.
"""

import json
import logging
import os
from datetime import datetime
from uuid import uuid4

from models.knowledge_base import (
    EnforcementAction,
    KnowledgeBaseStats,
    RegulatoryDocument,
    RetrievedPrecedent,
)

logger = logging.getLogger(__name__)

# ChromaDB collection dedicated to the knowledge base (separate from uploads)
COLLECTION_NAME = "knowledge_base"

# Default JSON-backed store location
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")

RECORD_REGULATORY = "regulatory_document"
RECORD_ENFORCEMENT = "enforcement_action"


class KnowledgeBaseService:
    """
    Stores and retrieves regulatory documents and greenwashing enforcement
    actions used as precedents during claim analysis.

    Dependencies are injected so tests can supply fakes and run offline:
        KnowledgeBaseService(
            embedding_service=FakeEmbeddings(),
            chroma_client=FakeChromaClient(),
            data_dir=str(tmp_path),
        )
    """

    def __init__(
        self,
        embedding_service=None,
        chroma_client=None,
        data_dir: str | None = None,
        collection_name: str = COLLECTION_NAME,
    ):
        self.data_dir = data_dir or _DATA_DIR
        self.collection_name = collection_name
        self.documents_file = os.path.join(self.data_dir, "regulatory_documents.json")
        self.enforcement_file = os.path.join(self.data_dir, "enforcement_actions.json")

        self._embedding_service = embedding_service
        self._chroma_client = chroma_client
        self._collection = None

        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(
            f"KnowledgeBaseService initialized — data dir: {self.data_dir}, "
            f"collection: {self.collection_name}"
        )

    # ------------------------------------------------------------------
    # Lazy dependencies
    # ------------------------------------------------------------------

    @property
    def embedding_service(self):
        """Embedding service — loaded lazily so tests can inject a fake."""
        if self._embedding_service is None:
            from services.embedding_service import EmbeddingService

            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def client(self):
        """ChromaDB client — reuses the shared persistent client by default."""
        if self._chroma_client is None:
            from services.vector_store import _get_client

            self._chroma_client = _get_client()
        return self._chroma_client

    def _get_collection(self):
        """Get or create the dedicated knowledge base collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"kind": "knowledge_base", "hnsw:space": "cosine"},
            )
        return self._collection

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def add_regulatory_document(self, doc: RegulatoryDocument) -> str:
        """
        Chunk, embed, and store a regulatory document.

        Returns the document id (generated if the incoming id is empty).
        """
        if not doc.content or not doc.content.strip():
            raise ValueError("RegulatoryDocument.content must be non-empty")

        if not doc.id:
            doc.id = str(uuid4())

        chunks = self.embedding_service.chunk_text(doc.content)
        if not chunks:
            chunks = [doc.content]

        embeddings = self.embedding_service.embed_batch(chunks)

        ids = [f"{doc.id}::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "record_type": RECORD_REGULATORY,
                "record_id": doc.id,
                "title": doc.title,
                "jurisdiction": doc.jurisdiction,
                "document_type": doc.document_type,
                "chunk_index": i,
                "url": doc.url or "",
            }
            for i in range(len(chunks))
        ]

        self._store_chunks(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        self._upsert_record(self.documents_file, doc.id, doc)

        logger.info(
            f"Added regulatory document {doc.id} '{doc.title}' "
            f"({doc.jurisdiction}, {len(chunks)} chunks)"
        )
        return doc.id

    async def add_enforcement_action(self, action: EnforcementAction) -> str:
        """
        Store a greenwashing enforcement action with structured metadata.

        Returns the action id (generated if the incoming id is empty).
        """
        if not action.id:
            action.id = str(uuid4())

        text = self._enforcement_text(action)
        embedding = self.embedding_service.embed(text)

        metadata = {
            "record_type": RECORD_ENFORCEMENT,
            "record_id": action.id,
            "title": f"{action.company_name} — {action.violation_type}",
            "jurisdiction": action.jurisdiction,
            "document_type": RECORD_ENFORCEMENT,
            "chunk_index": 0,
            "company_name": action.company_name,
            "violation_type": action.violation_type,
            "ruling_date": action.ruling_date.isoformat(),
            "source_url": action.source_url or "",
        }

        self._store_chunks(
            ids=[f"{action.id}::0"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        self._upsert_record(self.enforcement_file, action.id, action)

        logger.info(
            f"Added enforcement action {action.id} against {action.company_name} "
            f"({action.jurisdiction}, {action.violation_type})"
        )
        return action.id

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def query_precedents(
        self,
        claim_text: str,
        jurisdiction: str | None = None,
        k: int = 3,
    ) -> list[RetrievedPrecedent]:
        """
        Retrieve the k most relevant regulatory precedents for a claim.

        When `jurisdiction` is provided, only chunks tagged with that
        jurisdiction are returned.
        """
        if not claim_text or not claim_text.strip() or k <= 0:
            return []

        collection = self._get_collection()
        total = collection.count()
        if total == 0:
            return []

        embedding = self.embedding_service.embed(claim_text)
        where = {"jurisdiction": jurisdiction} if jurisdiction else None

        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(k, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = (results.get("ids") or [[]])[0]
        if not ids:
            return []

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        enforcement_records = self._read_records(self.enforcement_file)

        precedents: list[RetrievedPrecedent] = []
        for i in range(len(ids)):
            metadata = metadatas[i] or {}
            distance = distances[i] if i < len(distances) else None

            action = None
            if metadata.get("record_type") == RECORD_ENFORCEMENT:
                raw = enforcement_records.get(metadata.get("record_id", ""))
                if raw is not None:
                    try:
                        action = EnforcementAction.model_validate(raw)
                    except Exception as e:  # pragma: no cover - defensive
                        logger.warning(f"Could not parse enforcement action: {e}")

            precedents.append(
                RetrievedPrecedent(
                    document_title=metadata.get("title", ""),
                    jurisdiction=metadata.get("jurisdiction", ""),
                    excerpt=documents[i] if i < len(documents) else "",
                    relevance_score=self._relevance_from_distance(distance),
                    enforcement_action=action,
                )
            )

        return precedents[:k]

    async def get_stats(self) -> KnowledgeBaseStats:
        """Return document counts by type and jurisdiction."""
        documents = self._read_records(self.documents_file)
        actions = self._read_records(self.enforcement_file)

        by_jurisdiction: dict[str, int] = {}
        for record in list(documents.values()) + list(actions.values()):
            jurisdiction = record.get("jurisdiction", "") or "UNKNOWN"
            by_jurisdiction[jurisdiction] = by_jurisdiction.get(jurisdiction, 0) + 1

        return KnowledgeBaseStats(
            regulatory_documents=len(documents),
            enforcement_actions=len(actions),
            by_jurisdiction=by_jurisdiction,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _enforcement_text(action: EnforcementAction) -> str:
        """Build the searchable text representation of an enforcement action."""
        parts = [
            f"{action.company_name} — {action.violation_type}",
            action.summary,
            f"Jurisdiction: {action.jurisdiction}",
            f"Ruling date: {action.ruling_date.date().isoformat()}",
        ]
        if action.fine_amount is not None:
            parts.append(f"Fine: {action.fine_amount:,.0f} {action.fine_currency}")
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _relevance_from_distance(distance: float | None) -> float:
        """
        Map a cosine distance (0..2) to a relevance score in [0.0, 1.0].
        Missing distances fall back to a neutral score.
        """
        if distance is None:
            return 0.5
        score = 1.0 - (float(distance) / 2.0)
        return max(0.0, min(1.0, score))

    def _store_chunks(self, ids, embeddings, documents, metadatas) -> None:
        """Upsert chunks into the knowledge base collection."""
        collection = self._get_collection()
        upsert = getattr(collection, "upsert", None)
        if callable(upsert):
            upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        else:  # pragma: no cover - older chroma clients
            collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def _read_records(self, path: str) -> dict[str, dict]:
        """Read a JSON record store keyed by record id."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read knowledge base store {path}: {e}")
            return {}

        if isinstance(data, dict):
            return {str(key): value for key, value in data.items() if isinstance(value, dict)}
        if isinstance(data, list):
            return {
                str(item.get("id", "")): item
                for item in data
                if isinstance(item, dict) and item.get("id")
            }
        return {}

    def _upsert_record(self, path: str, record_id: str, model) -> None:
        """Insert or replace a record in the JSON store."""
        records = self._read_records(path)
        payload = model.model_dump(mode="json")
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        records[record_id] = payload

        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
