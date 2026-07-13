"""
Experience scorer — 30% weight of total ATS score.

Bands:
    total_years >= preferred_years   → 30.0 (full score)
    total_years >= min_years         → 20.0
    total_years >= min_years * 0.5   → 10.0
    total_years < min_years * 0.5    →  0.0
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MAX_SCORE: float = 30.0


@dataclass
class ExperienceScoreResult:
    score: float
    total_months: int
    total_years: float
    min_years_required: int
    preferred_years: int


def score_experience(
    total_months: int,
    min_experience_years: int,
    preferred_experience_years: int,
    max_score: float = MAX_SCORE,
) -> ExperienceScoreResult:
    """
    Compute the experience component score (out of 30 by default).

    Args:
        total_months: Aggregated months of work experience from resume.
        min_experience_years: Minimum required years from job profile.
        preferred_experience_years: Ideal years for full score.
        max_score: The maximum score weight for this component.

    Returns:
        ExperienceScoreResult with score and summary.
    """
    total_years = total_months / 12.0

    if total_years >= preferred_experience_years:
        score = max_score
    elif total_years >= min_experience_years:
        # M5 Fix: Linear interpolation between min and preferred
        denom = preferred_experience_years - min_experience_years
        if denom <= 0:
            ratio = 1.0  # min == preferred means candidate fully qualifies
        else:
            ratio = (total_years - min_experience_years) / denom
        score = (2.0 / 3.0) * max_score + ratio * (1.0 / 3.0) * max_score
    elif total_years >= min_experience_years * 0.5:
        score = (1.0 / 3.0) * max_score
    else:
        score = 0.0

    score = round(min(score, max_score), 2)
    logger.debug(
        "Experience score: %.2f/%.0f (%.1f years, min=%d, preferred=%d)",
        score, max_score, total_years, min_experience_years, preferred_experience_years,
    )
    return ExperienceScoreResult(
        score=score,
        total_months=total_months,
        total_years=round(total_years, 1),
        min_years_required=min_experience_years,
        preferred_years=preferred_experience_years,
    )
