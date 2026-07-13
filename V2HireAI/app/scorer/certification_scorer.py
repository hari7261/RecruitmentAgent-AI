"""
Certification scorer — 10% weight of total ATS score.

Rules:
    required_certs all matched → base 7.0
    preferred_certs matched    → up to 3.0 bonus
    Total capped at 10.0
"""
import logging
import re
from dataclasses import dataclass

from app.extractor.certification_extractor import CertificationEntry

logger = logging.getLogger(__name__)

MAX_SCORE: float = 10.0


@dataclass
class CertScoreResult:
    score: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]


def score_certifications(
    cert_entries: list[CertificationEntry],
    required_certs: list[str],
    preferred_certs: list[str],
    max_score: float = MAX_SCORE,
) -> CertScoreResult:
    """
    Compute the certification component score (out of 10 by default).

    Args:
        cert_entries: Extracted certifications from resume.
        required_certs: Patterns for required certs from job profile.
        preferred_certs: Patterns for preferred certs from job profile.
        max_score: The maximum score weight for this component.

    Returns:
        CertScoreResult with score and match details.
    """
    cert_texts = [c.name.lower() for c in cert_entries]

    def _matches_any(pattern: str) -> bool:
        """Check if any extracted cert contains the pattern keyword."""
        p = re.compile(re.escape(pattern.lower()))
        return any(p.search(ct) for ct in cert_texts)

    matched_req, missing_req = [], []
    for req in required_certs:
        (matched_req if _matches_any(req) else missing_req).append(req)

    matched_pref = [p for p in preferred_certs if _matches_any(p)]

    # Scoring
    req_max = 0.7 * max_score
    pref_max = 0.3 * max_score

    if not required_certs:
        # No required certs — score purely on preferred
        req_score = req_max  # Give full required portion if none required
    else:
        req_pct = len(matched_req) / len(required_certs) if required_certs else 1.0
        req_score = req_pct * req_max

    pref_pct = len(matched_pref) / len(preferred_certs) if preferred_certs else 0.0
    pref_score = pref_pct * pref_max

    score = round(min(req_score + pref_score, max_score), 2)

    logger.debug(
        "Cert score: %.2f/%.0f (req=%d/%d pref=%d/%d)",
        score, max_score,
        len(matched_req), len(required_certs),
        len(matched_pref), len(preferred_certs),
    )
    return CertScoreResult(
        score=score,
        matched_required=matched_req,
        missing_required=missing_req,
        matched_preferred=matched_pref,
    )
