"""
EasyOCR fallback parser for scanned/image-based PDFs.

Only imported when Docling fails to extract sufficient text.
Uses pdf2image to render PDF pages to images, then EasyOCR for text.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# EasyOCR reader is expensive to initialize — cache it as a module-level singleton
_ocr_reader = None


def _get_ocr_reader():
    """Lazy-initialize the EasyOCR reader (English only)."""
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Initializing EasyOCR reader (first use — this may take a moment).")
        import easyocr  # type: ignore[import-untyped]
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


def ocr_pdf(file_path: Path) -> str:
    """
    Extract text from a scanned PDF using EasyOCR.

    Steps:
    1. Convert each PDF page to a PIL image via pdf2image.
    2. Run EasyOCR on each image.
    3. Join all text with newlines.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Concatenated OCR text from all pages.
    """
    try:
        import pdf2image  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "pdf2image is required for OCR fallback. Install it with: pip install pdf2image"
        ) from exc

    logger.info("Running EasyOCR on: %s", file_path.name)
    reader = _get_ocr_reader()

    pages = pdf2image.convert_from_path(str(file_path), dpi=200)
    logger.info("OCR: %d pages to process.", len(pages))

    all_text: list[str] = []
    for i, page_image in enumerate(pages, start=1):
        import numpy as np  # type: ignore[import-untyped]
        image_array = np.array(page_image)
        results = reader.readtext(image_array, detail=0, paragraph=True)
        page_text = "\n".join(results)
        all_text.append(page_text)
        logger.debug("OCR page %d/%d: %d chars", i, len(pages), len(page_text))

    return "\n\n".join(all_text)
