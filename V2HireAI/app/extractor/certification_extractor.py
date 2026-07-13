"""
Certification extractor.

Detects and extracts professional certifications from resume text using:
- Section-based isolation (CERTIFICATIONS, LICENSES, etc.)
- Keyword pattern matching for common certification issuers
- Year extraction via regex
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.utils.text_cleaner import extract_section_text, remove_bullets

logger = logging.getLogger(__name__)

_CERT_HEADERS = [
    "certifications", "licenses", "credentials",
    "certifications & licenses", "professional certifications",
    "certificates", "accreditations",
]

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Known certification issuer keywords (expand as needed)
_CERT_ISSUER_PATTERNS = re.compile(
    r"\b(?:"
    r"AWS|Amazon Web Services|"
    r"Google|GCP|"
    r"Microsoft|Azure|"
    r"Kubernetes|CKA|CKAD|CKS|"
    r"HashiCorp|Terraform|"
    r"CompTIA|"
    r"Cisco|CCNA|CCNP|CCIE|"
    r"Oracle|OCP|"
    r"Red Hat|RHCE|RHCSA|"
    r"Scrum|PSM|CSM|SAFe|"
    r"PMI|PMP|CAPM|"
    r"ISACA|CISSP|CISM|CISA|"
    r"CFA|FRM|"
    r"Salesforce|"
    r"MongoDB|"
    r"Databricks|"
    r"Snowflake|"
    r"Linux Foundation|"
    r"Coursera|Udemy|edX|Pluralsight"
    r")\b",
    re.IGNORECASE,
)

@dataclass
class CertificationEntry:
    name: str
    issuer: Optional[str] = None
    year: Optional[int] = None
    credential_id: Optional[str] = None


def extract_certifications(text: str) -> list[CertificationEntry]:
    """
    Extract certifications from resume text.

    First tries the dedicated certifications section.
    Falls back to scanning the full text for certification patterns.

    Returns:
        List of CertificationEntry objects.
    """
    section = extract_section_text(text, _CERT_HEADERS)
    if section:
        entries = _parse_cert_section(section)
    else:
        # Fallback: scan full text for cert keywords
        entries = _scan_full_text(text)

    logger.debug("Extracted %d certifications.", len(entries))
    return entries


def _parse_cert_section(section: str) -> list[CertificationEntry]:
    """Parse the certifications section line by line."""
    entries: list[CertificationEntry] = []
    for line in section.split("\n"):
        line = remove_bullets(line).strip()
        if not line or len(line) < 5:
            continue

        year = _extract_year(line)
        issuer = _extract_issuer(line)
        credential_id = _extract_credential_id(line)

        entries.append(
            CertificationEntry(
                name=line[:300],
                issuer=issuer,
                year=year,
                credential_id=credential_id,
            )
        )
    return entries


def _scan_full_text(text: str) -> list[CertificationEntry]:
    """Scan full resume text for lines containing certification keywords."""
    entries: list[CertificationEntry] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _CERT_ISSUER_PATTERNS.search(stripped):
            # Heuristic: line must contain "certif" or "certified" or issuer name
            if re.search(r"\bcertif", stripped, re.IGNORECASE) or (
                _CERT_ISSUER_PATTERNS.search(stripped)
                and len(stripped.split()) <= 15
            ):
                year = _extract_year(stripped)
                issuer = _extract_issuer(stripped)
                entries.append(
                    CertificationEntry(
                        name=stripped[:300],
                        issuer=issuer,
                        year=year,
                    )
                )
    return entries[:20]  # Cap to avoid noise


def _extract_year(text: str) -> Optional[int]:
    m = _YEAR_RE.search(text)
    return int(m.group(0)) if m else None


def _extract_issuer(text: str) -> Optional[str]:
    m = _CERT_ISSUER_PATTERNS.search(text)
    return m.group(0) if m else None


def _extract_credential_id(text: str) -> Optional[str]:
    m = re.search(
        r"(?:credential|cert(?:ificate)?|id|no|#)[:\s#]+([A-Z0-9\-]{6,30})",
        text,
        re.IGNORECASE,
    )
    return m.group(1) if m else None
