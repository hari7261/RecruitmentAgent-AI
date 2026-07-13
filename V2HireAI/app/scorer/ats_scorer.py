"""
ATS Scoring orchestrator.

Loads job_profile.yaml and delegates to each sub-scorer.
Computes total score and hiring recommendation.
"""
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from app.core.config import settings
from app.extractor.certification_extractor import CertificationEntry
from app.extractor.education_extractor import EducationEntry
from app.extractor.project_extractor import ProjectEntry
from app.matcher.skill_matcher import match_skills
from app.scorer.skill_scorer import SkillScoreResult, score_skills
from app.scorer.experience_scorer import ExperienceScoreResult, score_experience
from app.scorer.education_scorer import EducationScoreResult, score_education
from app.scorer.certification_scorer import CertScoreResult, score_certifications
from app.scorer.project_scorer import ProjectScoreResult, score_projects

logger = logging.getLogger(__name__)


@dataclass
class ATSScoringInput:
    """All extracted data required to compute an ATS score."""
    extracted_skills: list[str] = field(default_factory=list)
    total_experience_months: int = 0
    education_entries: list[EducationEntry] = field(default_factory=list)
    certification_entries: list[CertificationEntry] = field(default_factory=list)
    project_entries: list[ProjectEntry] = field(default_factory=list)


@dataclass
class ATSScoringResult:
    """Complete ATS scoring output with component breakdown."""
    skill_score: float
    experience_score: float
    education_score: float
    certification_score: float
    project_score: float
    total_score: float
    recommendation: str

    # Detailed breakdowns
    skill_details: SkillScoreResult = field(default_factory=lambda: SkillScoreResult(0, 0, 0, [], [], []))
    experience_details: ExperienceScoreResult = field(
        default_factory=lambda: ExperienceScoreResult(0, 0, 0.0, 0, 0)
    )
    education_details: EducationScoreResult = field(
        default_factory=lambda: EducationScoreResult(0, None, [])
    )
    cert_details: CertScoreResult = field(default_factory=lambda: CertScoreResult(0, [], [], []))
    project_details: ProjectScoreResult = field(
        default_factory=lambda: ProjectScoreResult(0, 0, 0, 0)
    )


@lru_cache(maxsize=10)
def _load_job_profile(profile_key: str = "default") -> dict:
    """Load and cache the job profile YAML."""
    if profile_key and profile_key != "default":
        config_path = Path(settings.job_profile_path).parent / f"job_profile_{profile_key}.yaml"
    else:
        config_path = Path(settings.job_profile_path)

    if not config_path.exists():
        # Fall back to main default profile if specific vacancy profile is missing
        config_path = Path(settings.job_profile_path)

    if not config_path.exists():
        logger.warning("Job profile not found at %s — using defaults.", config_path)
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_recommendation(total_score: float) -> str:
    """
    Deterministic hiring recommendation based on total score.

    Thresholds (configurable via Settings):
        90-100 → Strong Hire
        75-89  → Hire
        60-74  → Review
        < 60   → Reject
    """
    if total_score >= settings.strong_hire_threshold:
        return "Strong Hire"
    elif total_score >= settings.hire_threshold:
        return "Hire"
    elif total_score >= settings.review_threshold:
        return "Review"
    else:
        return "Reject"


def compute_ats_score(scoring_input: ATSScoringInput, job_profile: Any = "default") -> ATSScoringResult:
    """
    Compute the full ATS score for a resume.

    Args:
        scoring_input: All extracted data from the resume.
        job_profile: The vacancy profile to score against (JobProfile, dict, or string).

    Returns:
        ATSScoringResult with total score, breakdown, and recommendation.
    """
    if hasattr(job_profile, "required_skills"):
        # It's an ORM JobProfile model
        required_skills = job_profile.required_skills or []
        preferred_skills = job_profile.preferred_skills or []
        min_exp_years = job_profile.min_experience_years or 0
        preferred_exp_years = job_profile.preferred_experience_years or 5
        preferred_education = job_profile.preferred_education or []
        required_certs = job_profile.required_certifications or []
        preferred_certs = job_profile.preferred_certifications or []
        min_projects = job_profile.min_projects or 1
        preferred_projects = job_profile.preferred_projects or 3
        weights = job_profile.scoring_weights or {}
    elif isinstance(job_profile, dict):
        required_skills = job_profile.get("required_skills", [])
        preferred_skills = job_profile.get("preferred_skills", [])
        min_exp_years = job_profile.get("min_experience_years", 2)
        preferred_exp_years = job_profile.get("preferred_experience_years", 5)
        preferred_education = job_profile.get("preferred_education", [])
        required_certs = job_profile.get("required_certifications", [])
        preferred_certs = job_profile.get("preferred_certifications", [])
        min_projects = job_profile.get("min_projects", 1)
        preferred_projects = job_profile.get("preferred_projects", 3)
        weights = job_profile.get("scoring_weights", {}) or {}
    else:
        profile = _load_job_profile(job_profile)
        required_skills = profile.get("required_skills", [])
        preferred_skills = profile.get("preferred_skills", [])
        min_exp_years = profile.get("min_experience_years", 2)
        preferred_exp_years = profile.get("preferred_experience_years", 5)
        preferred_education = profile.get("preferred_education", [])
        required_certs = profile.get("required_certifications", [])
        preferred_certs = profile.get("preferred_certifications", [])
        min_projects = profile.get("min_projects", 1)
        preferred_projects = profile.get("preferred_projects", 3)
        weights = profile.get("scoring_weights", {}) or {}

    # Extract dynamic weights with default fallbacks
    w_skills = float(weights.get("skills") if weights.get("skills") is not None else 40.0)
    w_experience = float(weights.get("experience") if weights.get("experience") is not None else 30.0)
    w_education = float(weights.get("education") if weights.get("education") is not None else 10.0)
    w_certs = float(weights.get("certifications") if weights.get("certifications") is not None else 10.0)
    w_projects = float(weights.get("projects") if weights.get("projects") is not None else 10.0)

    # ── Skills (dynamic weight) ──────────────────────────────────────────────
    skill_match = match_skills(
        extracted=scoring_input.extracted_skills,
        required=required_skills,
        preferred=preferred_skills,
    )
    skill_result = score_skills(skill_match, max_score=w_skills)

    # ── Experience (dynamic weight) ──────────────────────────────────────────
    exp_result = score_experience(
        total_months=scoring_input.total_experience_months,
        min_experience_years=min_exp_years,
        preferred_experience_years=preferred_exp_years,
        max_score=w_experience,
    )

    # ── Education (dynamic weight) ───────────────────────────────────────────
    edu_result = score_education(
        education_entries=scoring_input.education_entries,
        preferred_education=preferred_education,
        max_score=w_education,
    )

    # ── Certifications (dynamic weight) ──────────────────────────────────────
    cert_result = score_certifications(
        cert_entries=scoring_input.certification_entries,
        required_certs=required_certs,
        preferred_certs=preferred_certs,
        max_score=w_certs,
    )

    # ── Projects (dynamic weight) ────────────────────────────────────────────
    proj_result = score_projects(
        project_entries=scoring_input.project_entries,
        min_projects=min_projects,
        preferred_projects=preferred_projects,
        max_score=w_projects,
    )

    total = round(
        skill_result.score
        + exp_result.score
        + edu_result.score
        + cert_result.score
        + proj_result.score,
        2,
    )

    # Normalize recommendation thresholds if custom weights don't sum to 100
    sum_of_weights = w_skills + w_experience + w_education + w_certs + w_projects
    normalized_score = total
    if sum_of_weights > 0 and sum_of_weights != 100.0:
        normalized_score = (total / sum_of_weights) * 100.0

    recommendation = _get_recommendation(normalized_score)

    logger.info(
        "ATS Score: %.1f | %s (S=%.1f/%.1f E=%.1f/%.1f Ed=%.1f/%.1f C=%.1f/%.1f P=%.1f/%.1f)",
        total, recommendation,
        skill_result.score, w_skills,
        exp_result.score, w_experience,
        edu_result.score, w_education,
        cert_result.score, w_certs,
        proj_result.score, w_projects,
    )

    return ATSScoringResult(
        skill_score=skill_result.score,
        experience_score=exp_result.score,
        education_score=edu_result.score,
        certification_score=cert_result.score,
        project_score=proj_result.score,
        total_score=total,
        recommendation=recommendation,
        skill_details=skill_result,
        experience_details=exp_result,
        education_details=edu_result,
        cert_details=cert_result,
        project_details=proj_result,
    )
