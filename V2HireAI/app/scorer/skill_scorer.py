"""
Skill scorer — 40% weight of total ATS score.

Formula:
    score = (required_match_pct * 0.7 + preferred_match_pct * 0.3) * MAX_SCORE
"""
import logging
from dataclasses import dataclass

from app.matcher.skill_matcher import SkillMatchResult

logger = logging.getLogger(__name__)

MAX_SCORE: float = 40.0


@dataclass
class SkillScoreResult:
    score: float
    required_match_pct: float
    preferred_match_pct: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]


def score_skills(match_result: SkillMatchResult, max_score: float = MAX_SCORE) -> SkillScoreResult:
    """
    Compute the skills component score (out of 40 by default).

    Args:
        match_result: Result from skill_matcher.match_skills().
        max_score: The maximum score weight for this component.

    Returns:
        SkillScoreResult with score and breakdown details.
    """
    req_pct = match_result.required_match_pct
    pref_pct = match_result.preferred_match_pct

    # M6 Fix: When required list is empty, treat as 100% match (or use preferred-only)
    total_required = len(match_result.matched_required) + len(match_result.missing_required)
    if total_required == 0:
        # No required skills specified - use preferred only
        weighted = pref_pct
    else:
        weighted = req_pct * 0.7 + pref_pct * 0.3
    
    score = round(min(weighted * max_score, max_score), 2)

    logger.debug(
        "Skill score: %.2f/%.0f (req=%.0f%% pref=%.0f%%)",
        score, max_score, req_pct * 100, pref_pct * 100,
    )
    return SkillScoreResult(
        score=score,
        required_match_pct=req_pct,
        preferred_match_pct=pref_pct,
        matched_required=match_result.matched_required,
        missing_required=match_result.missing_required,
        matched_preferred=match_result.matched_preferred,
    )
