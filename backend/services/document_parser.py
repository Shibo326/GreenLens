import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Performance: cap document text to prevent huge files from slowing analysis.
# ~8000 chars ≈ 2000 words — more than enough for contract/sustainability report analysis.
MAX_DOC_CHARS = 8000


class ExtractionError(Exception):
    """Raised when text extraction from a document fails unrecoverably."""
    pass


class DocumentParser:
    """Extracts plain text from PDF files and images."""

    SUPPORTED_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        """
        Extract plain text from file bytes.

        Args:
            file_bytes: Raw file content
            mime_type: MIME type string (e.g. "application/pdf", "image/png")

        Returns:
            Extracted plain text string (truncated to MAX_DOC_CHARS for performance)

        Raises:
            ExtractionError: If extraction fails unrecoverably
        """
        if mime_type == "application/pdf":
            text = self._extract_pdf(file_bytes)
        elif mime_type in ("image/png", "image/jpeg", "image/jpg"):
            text = self._extract_image(file_bytes)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = self._extract_docx(file_bytes)
        else:
            raise ExtractionError(f"Unsupported MIME type: {mime_type}")

        # Truncate oversized documents to keep LLM calls fast
        if len(text) > MAX_DOC_CHARS:
            logger.warning(
                f"Document truncated from {len(text)} to {MAX_DOC_CHARS} chars for performance."
            )
            text = text[:MAX_DOC_CHARS]

        return text

    def _extract_pdf(self, file_bytes: bytes) -> str:
        """
        Extract text from a PDF using PyMuPDF (fitz).
        Falls back to pytesseract OCR for image-only pages.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ExtractionError(f"PyMuPDF not available: {e}")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ExtractionError(f"Failed to open PDF: {e}")

        pages_text = []
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                text = page.get_text("text")

                # If no text found on this page, try OCR fallback
                if not text.strip():
                    logger.debug(
                        f"Page {page_num + 1} has no extractable text, falling back to OCR"
                    )
                    ocr_text = self._ocr_pdf_page(page)
                    if ocr_text:
                        text = ocr_text

                pages_text.append(text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                pages_text.append("")

        doc.close()
        full_text = "\n".join(pages_text)

        if not full_text.strip():
            raise ExtractionError("No text could be extracted from the PDF")

        return full_text

    def _ocr_pdf_page(self, page) -> str:
        """
        Perform OCR on a single PDF page by rendering it to an image.
        Used as fallback for image-only PDF pages.
        """
        try:
            import fitz
            from PIL import Image
            import pytesseract

            # Render page at 2x resolution for better OCR quality
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            image = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.warning(f"OCR fallback failed for PDF page: {e}")
            return ""

    def _extract_image(self, file_bytes: bytes) -> str:
        """
        Extract text from an image file using pytesseract + Pillow OCR.
        Falls back to basic image metadata description if Tesseract is not installed.
        """
        try:
            from PIL import Image
        except ImportError as e:
            raise ExtractionError(f"Pillow not available: {e}")

        try:
            image = Image.open(io.BytesIO(file_bytes))
            # Convert to RGB if needed (handles RGBA, grayscale, etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
        except Exception as e:
            raise ExtractionError(f"Failed to open image: {e}")

        # Try pytesseract OCR first
        try:
            import pytesseract
            text = pytesseract.image_to_string(image)
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"Tesseract OCR not available or failed: {e}")

        # Fallback: return image metadata as context
        # This allows the system to at least acknowledge the image was uploaded
        width, height = image.size
        mode = image.mode
        file_size_kb = len(file_bytes) / 1024
        
        fallback_text = (
            f"[Image uploaded: {width}x{height} pixels, {mode} mode, {file_size_kb:.1f} KB. "
            f"OCR could not extract text from this image. The image may contain visual content "
            f"such as diagrams, photos, or graphics that require visual interpretation.]"
        )
        return fallback_text

    def _extract_docx(self, file_bytes: bytes) -> str:
        """
        Extract text from a DOCX file using python-docx.
        """
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            if not text.strip():
                raise ExtractionError("No text could be extracted from the DOCX")
            return text
        except ImportError as e:
            raise ExtractionError(f"python-docx not available: {e}")
        except Exception as e:
            raise ExtractionError(f"Failed to extract DOCX: {e}")
