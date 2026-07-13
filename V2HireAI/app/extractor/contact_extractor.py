"""
Contact information extractor.

Extracts Name, Email, and Phone from resume text using:
- Regex for email and phone (deterministic, high accuracy)
- spaCy NER for name (PERSON entity in first N lines)
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Regex Patterns ─────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?"       # Country code (+91, +1, 1)
    r"(?:\(?\d{2,5}\)?[-.\s]?)?"     # Area code (2-5 digits, optional brackets)
    r"\d{3,5}"                       # 1st group (3-5 digits)
    r"[-.\s]?"                       # Separator
    r"\d{3,5}"                       # 2nd group (3-5 digits)
    r"(?:[-.\s]?\d{3,5})?",          # 3rd group (optional, e.g. for US 3-3-4 structure)
)

# Noise phrases that should never be extracted as phone numbers
_PHONE_NOISE = re.compile(r"^\d{4}$|^\d{6}$|^\d{10}$(?![\w])")

# ── spaCy (lazy load) ─────────────────────────────────────────────────────────
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        from app.core.config import settings
        try:
            _nlp = spacy.load(settings.spacy_model)
        except OSError:
            logger.warning(
                "spaCy model '%s' not found. Install with: "
                "python -m spacy download %s",
                settings.spacy_model, settings.spacy_model,
            )
            _nlp = None
    return _nlp


@dataclass
class ContactInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


def extract_contact(text: str) -> ContactInfo:
    """
    Extract contact information from resume text.

    Args:
        text: Full cleaned resume text.

    Returns:
        ContactInfo dataclass with name, email, phone fields.
    """
    email = _extract_email(text)
    phone = _extract_phone(text)
    name = _extract_name(text)
    logger.debug("Contact extracted — name=%r email=%r phone=%r", name, email, phone)
    return ContactInfo(name=name, email=email, phone=phone)


def _extract_email(text: str) -> Optional[str]:
    """Return the first valid email address found in the text."""
    match = _EMAIL_RE.search(text)
    return match.group(0).lower() if match else None


def _extract_phone(text: str) -> Optional[str]:
    """Return the first plausible phone number found in the text."""
    for match in _PHONE_RE.finditer(text):
        raw = match.group(0).strip()
        # Reject if it looks like a year, ZIP, or other numeric noise
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 7 or len(digits) > 15:
            continue
        return raw
    return None


def _extract_name(text: str) -> Optional[str]:
    """
    Extract the candidate's name using spaCy PERSON NER.

    Searches only the first 10 lines to avoid picking up company names
    or other PERSON entities deeper in the resume.
    """
    nlp = _get_nlp()
    if nlp is None:
        return _heuristic_name(text)

    header_text = "\n".join(text.split("\n")[:10])
    doc = nlp(header_text)

    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
            # Check if this PERSON entity is a substring of a clean title-cased line
            for line in header_text.split("\n"):
                line = line.strip()
                if ent.text in line:
                    # Clean contact info from line
                    line_clean = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "", line)
                    line_clean = re.sub(r"\+?\d[\d\-().\s]{7,}\d", "", line_clean)
                    line_clean = re.sub(r"\b(email|phone|mobile|tel|github|linkedin|contact|link|website)[:\s]*", "", line_clean, flags=re.I)
                    line_clean = re.sub(r"[|/\\•◦▪▸►→*·\-]", "", line_clean)
                    line_clean = line_clean.strip()
                    
                    words = line_clean.split()
                    if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()) and not re.search(r"[0-9]", line_clean):
                        return line_clean
            return ent.text.strip()

    return _heuristic_name(text)


def _heuristic_name(text: str) -> Optional[str]:
    """
    Fallback: treat the first non-empty line as the candidate's name
    if it looks like a proper name (title-cased, 2-4 words, no special chars).
    """
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Clean line
        line_clean = re.sub(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "", line)
        line_clean = re.sub(r"\+?\d[\d\-().\s]{7,}\d", "", line_clean)
        line_clean = re.sub(r"\b(email|phone|mobile|tel|github|linkedin|contact|link|website)[:\s]*", "", line_clean, flags=re.I)
        line_clean = re.sub(r"[|/\\•◦▪▸►→*·\-]", "", line_clean)
        line_clean = line_clean.strip()

        words = line_clean.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
            # Reject lines that look like headers or addresses
            if not re.search(r"[0-9@|/\\]", line_clean):
                return line_clean
    return None
