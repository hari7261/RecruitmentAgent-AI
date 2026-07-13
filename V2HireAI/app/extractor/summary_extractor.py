"""
Summary / Objective extractor.

Extracts the professional summary, objective, or profile section
from a resume. Returns raw text as-is (no further NLP processing).
"""
import logging
from typing import Optional

from app.utils.text_cleaner import extract_section_text

logger = logging.getLogger(__name__)

_SUMMARY_HEADERS = [
    "summary", "professional summary", "executive summary",
    "objective", "career objective", "professional objective",
    "profile", "professional profile",
    "about me", "about", "overview",
    "highlights", "key highlights",
]


def extract_summary(text: str) -> Optional[str]:
    """
    Extract the summary/objective section from resume text.

    Returns:
        Raw section text (up to 1000 chars) or None if not found.
    """
    section = extract_section_text(text, _SUMMARY_HEADERS)
    if not section:
        logger.debug("No summary section found.")
        return None

    # Truncate to a reasonable length
    summary = section.strip()[:1000]
    logger.debug("Extracted summary (%d chars).", len(summary))
    return summary
