"""
Skill matcher — compares extracted skills against job requirements.

Uses RapidFuzz token_sort_ratio for robust comparison of normalized
skill names. Produces a SkillMatchResult with counts and match percentage.
"""
import logging
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SkillMatchResult:
    """Result of matching extracted skills against required/preferred skills."""
    matched_required: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    matched_preferred: list[str] = field(default_factory=list)
    missing_preferred: list[str] = field(default_factory=list)
    additional_skills: list[str] = field(default_factory=list)

    @property
    def required_match_pct(self) -> float:
        """Percentage of required skills matched (0.0 - 1.0)."""
        total = len(self.matched_required) + len(self.missing_required)
        return len(self.matched_required) / total if total > 0 else 0.0

    @property
    def preferred_match_pct(self) -> float:
        """Percentage of preferred skills matched (0.0 - 1.0)."""
        total = len(self.matched_preferred) + len(self.missing_preferred)
        return len(self.matched_preferred) / total if total > 0 else 0.0


def match_skills(
    extracted: list[str],
    required: list[str],
    preferred: list[str],
) -> SkillMatchResult:
    """
    Match extracted normalized skills against required and preferred lists.

    Args:
        extracted: List of normalized skill names from the resume.
        required: Must-have skills from job profile.
        preferred: Nice-to-have skills from job profile.

    Returns:
        SkillMatchResult with match/miss breakdowns.
    """
    threshold = settings.fuzzy_match_threshold
    extracted_set = set(extracted)

    def _is_matched(skill: str) -> bool:
        """Check if a skill is in extracted (exact or fuzzy)."""
        if skill in extracted_set:
            return True
        if not extracted:
            return False
        matches = process.extract(
            skill,
            list(extracted_set),
            scorer=fuzz.token_sort_ratio,
            limit=1,
            score_cutoff=threshold,
        )
        return bool(matches)

    matched_req, missing_req = [], []
    for skill in required:
        (matched_req if _is_matched(skill) else missing_req).append(skill)

    matched_pref, missing_pref = [], []
    for skill in preferred:
        (matched_pref if _is_matched(skill) else missing_pref).append(skill)

    # Skills that are in the resume but not in required/preferred
    all_job_skills = set(required) | set(preferred)
    additional = [s for s in extracted if s not in all_job_skills]

    result = SkillMatchResult(
        matched_required=matched_req,
        missing_required=missing_req,
        matched_preferred=matched_pref,
        missing_preferred=missing_pref,
        additional_skills=additional,
    )
    logger.debug(
        "Skill match — required: %d/%d, preferred: %d/%d",
        len(matched_req), len(required),
        len(matched_pref), len(preferred),
    )
    return result
