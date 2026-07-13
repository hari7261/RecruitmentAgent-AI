"""
Document Parser — Exclusive parsing using Docling.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 50  # Threshold below which a parse result is considered empty


@dataclass
class ParsedDocument:
    text: str
    source: str  # Always "docling"


def parse_document(file_path: Path) -> ParsedDocument:
    """
    Parse a PDF or DOCX file to plain text using Docling only.

    Args:
        file_path: Absolute path to the uploaded file.

    Returns:
        ParsedDocument with extracted text and source.

    Raises:
        ParseError: If Docling fails or extracts insufficient text.
    """
    from app.core.exceptions import ParseError
    try:
        text = _parse_with_docling(file_path)
        if len(text.strip()) >= MIN_TEXT_CHARS:
            logger.info("Parsed '%s' with Docling (%d chars)", file_path.name, len(text))
            return ParsedDocument(text=text, source="docling")
        
        detail = f"Docling returned too little text ({len(text.strip())} chars)."
        logger.warning(detail)
        _raise_parse_error(file_path, detail)
    except ParseError:
        raise
    except Exception as exc:
        logger.warning("Docling failed for '%s': %s", file_path.name, exc)
        _raise_parse_error(file_path, str(exc))


def _parse_with_docling(file_path: Path) -> str:
    """Use Docling's backend (pypdfium2) for PDFs, and Docling converter for other files."""
    if file_path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(str(file_path)) as doc:
            return "\n".join(page.get_textpage().get_text_bounded() for page in doc)
    else:
        from docling.document_converter import DocumentConverter
        from docling_core.types.doc.document import ContentLayer
        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        return result.document.export_to_markdown(
            included_content_layers=[ContentLayer.BODY, ContentLayer.FURNITURE]
        )


def _raise_parse_error(file_path: Path, detail: str) -> None:
    """Raise a structured ParseError with context."""
    from app.core.exceptions import ParseError
    raise ParseError(
        message=f"Failed to extract text from '{file_path.name}' using Docling.",
        details={"file": str(file_path), "error": detail},
    )
