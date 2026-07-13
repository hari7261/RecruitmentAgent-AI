"""
app/models/__init__.py

Import all models here so that SQLAlchemy metadata is fully populated
before Alembic autogenerate or Base.metadata.create_all() is called.
"""
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.skill import Skill, CandidateSkill
from app.models.experience import Experience
from app.models.education import Education
from app.models.certification import Certification
from app.models.ats_score import ATSScore
from app.models.tenant import Tenant
from app.models.user import User
from app.models.subscription import Subscription
from app.models.opening import Opening
from app.models.job_profile import JobProfile
from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.invitation import Invitation

__all__ = [
    "Candidate",
    "Resume",
    "Skill",
    "CandidateSkill",
    "Experience",
    "Education",
    "Certification",
    "ATSScore",
    "Tenant",
    "User",
    "Subscription",
    "Opening",
    "JobProfile",
    "Application",
    "ApplicationStatusHistory",
    "Invitation",
]
