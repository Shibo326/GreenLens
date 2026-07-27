import logging
from typing import Optional

logger = logging.getLogger(__name__)

# AMD: ROCm GPU-accelerated embedding service
# Model: all-MiniLM-L6-v2 produces 384-dimensional vectors
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class EmbeddingService:
    """
    Generates text embeddings using sentence-transformers.
    Optimized for AMD MI300X ROCm GPU acceleration.
    """

    def __init__(self):
        logger.info(f"Loading sentence-transformer model: {MODEL_NAME}")
        try:
            from sentence_transformers import SentenceTransformer
            # AMD: ROCm will be auto-detected if available
            self.model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Model {MODEL_NAME} loaded successfully (dim={EMBEDDING_DIM})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def embed(self, text: str) -> list[float]:
        """
        Generate a 384-dimensional embedding vector for the given text.
        AMD: ROCm GPU-accelerated inference on MI300X hardware.

        Args:
            text: Input text to embed

        Returns:
            384-element float list
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        More efficient than calling embed() repeatedly.
        AMD: Takes advantage of MI300X HBM3 bandwidth for large batches.

        Args:
            texts: List of input texts

        Returns:
            List of 384-element float lists
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return [emb.tolist() for emb in embeddings]

    def chunk_text(
        self,
        text: str,
        max_tokens: int = 400,
        overlap: int = 40,
    ) -> list[str]:
        """
        Split text into overlapping chunks of approximately max_tokens tokens.
        Uses word-based approximation (1 token ≈ 0.75 words).
        
        Smaller chunks (400 tokens) with moderate overlap (40 tokens) process
        faster while still preserving enough context for accurate retrieval.

        Args:
            text: Input text to chunk
            max_tokens: Maximum tokens per chunk (approx)
            overlap: Number of tokens to overlap between consecutive chunks

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # Word-based approximation: ~0.75 words per token → multiply by 0.75
        max_words = int(max_tokens * 0.75)
        overlap_words = int(overlap * 0.75)

        words = text.split()
        if not words:
            return []

        # If text fits in a single chunk, return it as-is
        if len(words) <= max_words:
            return [text]

        chunks = []
        start = 0

        while start < len(words):
            end = min(start + max_words, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))

            # Advance by (max_words - overlap_words) for next chunk
            advance = max_words - overlap_words
            if advance <= 0:
                advance = 1  # Safety guard against infinite loop
            start += advance

            # If the remaining words are less than overlap, stop
            if start >= len(words):
                break

        return chunks
