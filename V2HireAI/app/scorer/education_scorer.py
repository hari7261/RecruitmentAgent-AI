"""
Education scorer — 10% weight of total ATS score.

Rules:
    Any normalized degree in preferred_education list → 10.0 (full score)
    No matching degree                                  →  0.0
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.extractor.education_extractor import EducationEntry

logger = logging.getLogger(__name__)

MAX_SCORE: float = 10.0


@dataclass
class EducationScoreResult:
    score: float
    matched_degree: Optional[str]
    all_degrees: list[str]


def score_education(
    education_entries: list[EducationEntry],
    preferred_education: list[str],
    max_score: float = MAX_SCORE,
) -> EducationScoreResult:
    """
    Compute the education component score (out of 10 by default).

    Args:
        education_entries: Extracted education entries from resume.
        preferred_education: Accepted normalized degree codes from job profile.
        max_score: The maximum score weight for this component.

    Returns:
        EducationScoreResult with score and matched degree info.
    """
    preferred_set = {d.lower() for d in preferred_education}
    all_degrees = [e.degree_normalized for e in education_entries if e.degree_normalized]

    matched_degree: Optional[str] = None
    for degree in all_degrees:
        if degree and degree.lower() in preferred_set:
            matched_degree = degree
            break

    score = max_score if matched_degree else 0.0

    logger.debug(
        "Education score: %.2f/%.0f (matched=%r degrees=%s)",
        score, max_score, matched_degree, all_degrees,
    )
    return EducationScoreResult(
        score=score,
        matched_degree=matched_degree,
        all_degrees=all_degrees,
    )
