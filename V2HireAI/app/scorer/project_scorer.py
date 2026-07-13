"""
Project scorer — 10% weight of total ATS score.

Rules:
    projects >= preferred_projects → 10.0
    projects >= min_projects       →  5.0 + linear interpolation
    projects == 0                  →  0.0
"""
import logging
from dataclasses import dataclass

from app.extractor.project_extractor import ProjectEntry

logger = logging.getLogger(__name__)

MAX_SCORE: float = 10.0


@dataclass
class ProjectScoreResult:
    score: float
    project_count: int
    min_projects: int
    preferred_projects: int


def score_projects(
    project_entries: list[ProjectEntry],
    min_projects: int,
    preferred_projects: int,
    max_score: float = MAX_SCORE,
) -> ProjectScoreResult:
    """
    Compute the project component score (out of 10 by default).

    Args:
        project_entries: Extracted project list from resume.
        min_projects: Minimum for partial score from job profile.
        preferred_projects: Count for full score from job profile.
        max_score: The maximum score weight for this component.

    Returns:
        ProjectScoreResult with score and count.
    """
    count = len(project_entries)

    if count == 0:
        score = 0.0
    elif count >= preferred_projects:
        score = max_score
    elif count >= min_projects:
        ratio = (count - min_projects) / max(preferred_projects - min_projects, 1)
        score = 0.5 * max_score + ratio * 0.5 * max_score
    else:
        # Partial credit even below minimum
        score = (count / max(min_projects, 1)) * 0.5 * max_score

    score = round(min(score, max_score), 2)
    logger.debug("Project score: %.2f/%.0f (count=%d)", score, max_score, count)
    return ProjectScoreResult(
        score=score,
        project_count=count,
        min_projects=min_projects,
        preferred_projects=preferred_projects,
    )
