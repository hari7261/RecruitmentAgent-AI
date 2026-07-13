"""
Resume Service — orchestrates the full upload → parse → extract → persist pipeline.

Responsibilities:
1. Validate uploaded file (size, extension, MIME)
2. Compute SHA-256, detect duplicates
3. Save file to uploads/
4. Parse document with Docling/OCR
5. Run all extractors
6. Persist Candidate + Resume + Skills + Experience + Education + Certifications
7. Trigger ATS scoring via ATSService
8. Return structured response
"""
import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DuplicateResumeError, ParseError, FileValidationError
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.models.skill import Skill, CandidateSkill
from app.models.experience import Experience
from app.models.education import Education
from app.models.certification import Certification
from app.repositories.resume_repository import ResumeRepository
from app.repositories.candidate_repository import CandidateRepository
from app.utils.file_validator import (
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
)
from app.utils.hash_utils import sha256_file
from app.utils.text_cleaner import clean_text
from app.parser.document_parser import parse_document
from app.extractor.contact_extractor import extract_contact
from app.extractor.skill_extractor import extract_skills
from app.extractor.experience_extractor import extract_experience
from app.extractor.education_extractor import extract_education
from app.extractor.certification_extractor import extract_certifications
from app.extractor.project_extractor import extract_projects
from app.extractor.summary_extractor import extract_summary
from app.scorer.ats_scorer import ATSScoringInput, compute_ats_score
from app.models.ats_score import ATSScore

logger = logging.getLogger(__name__)


class ResumeService:
    """
    Orchestrates the full resume processing pipeline.

    Designed for dependency injection — receives session and repositories
    as constructor arguments (no global state).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._resume_repo = ResumeRepository(session)
        self._candidate_repo = CandidateRepository(session)

    async def extract_contact_preview(self, upload_file: UploadFile) -> dict[str, str | None]:
        """
        Parse an uploaded resume without persisting it and return extracted contact data.

        Used by the public application flow to prefill candidate details
        before the final application submit.
        """
        filename = upload_file.filename or "unknown"
        ext = validate_file_extension(filename)

        content = await upload_file.read()
        validate_file_size(len(content))

        upload_dir = settings.upload_path
        tmp_path = upload_dir / f"preview_{uuid.uuid4().hex}.{ext}"

        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(content)

            await asyncio.to_thread(validate_mime_type, tmp_path, ext)
            parsed = await asyncio.to_thread(parse_document, tmp_path)
            clean = clean_text(parsed.text)
            contact = await asyncio.to_thread(extract_contact, clean)

            return {
                "name": contact.name.strip() if isinstance(contact.name, str) and contact.name.strip() else None,
                "email": contact.email.strip().lower() if isinstance(contact.email, str) and contact.email.strip() else None,
                "phone": contact.phone.strip() if isinstance(contact.phone, str) and contact.phone.strip() else None,
                "parse_source": parsed.source,
            }
        finally:
            tmp_path.unlink(missing_ok=True)

    async def upload_and_process(
        self,
        upload_file: UploadFile,
        job_profile: Any = "default",
        tenant_id: str = None,
        candidate_name: str | None = None,
        candidate_email: str | None = None,
        candidate_phone: str | None = None,
    ) -> Resume:
        """
        Full pipeline: validate → save → parse → extract → score → persist.
        Returns the fully populated Resume ORM instance.
        H6 Fix: Blocking CPU/IO operations offloaded to thread pool.
        """
        t_total = time.perf_counter()

        # ── Step 1: Validate ─────────────────────────────────────────────────
        filename = upload_file.filename or "unknown"
        ext = validate_file_extension(filename)

        content = await upload_file.read()
        validate_file_size(len(content))

        logger.info("Processing upload: '%s' (%d bytes)", filename, len(content))

        # ── Step 2: Save to disk ─────────────────────────────────────────────
        upload_dir = settings.upload_path
        tmp_path = upload_dir / f"tmp_{uuid.uuid4().hex}.{ext}"

        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(content)

        # ── Step 3: Hash + Duplicate Detection (offloaded — H6 Fix) ──────────
        file_hash = await asyncio.to_thread(sha256_file, tmp_path)
        effective_tenant_id = tenant_id or "default"
        existing = await self._resume_repo.get_by_hash(file_hash, tenant_id=effective_tenant_id)
        if existing:
            # M7 Fix: Return 409 instead of cascade-deleting (which would break applications)
            tmp_path.unlink(missing_ok=True)
            raise DuplicateResumeError(
                message="This file has already been uploaded.",
                details={"existing_resume_id": existing.id, "file_hash": file_hash},
            )

        # ── Step 3b: Subscription Limit Check ─────────────────────────────────
        if tenant_id:
            from app.repositories.subscription_repository import SubscriptionRepository
            from app.models.subscription import SubscriptionStatus
            sub_repo = SubscriptionRepository(self._session)
            subscription = await sub_repo.get_by_tenant(tenant_id)
            if subscription:
                if subscription.status == SubscriptionStatus.SUSPENDED:
                    from app.core.exceptions import SubscriptionLimitError
                    raise SubscriptionLimitError(message="Subscription is suspended")
                # Monthly resume limit enforcement is temporarily disabled.

        # Validate MIME type (offloaded — H6 Fix)
        try:
            await asyncio.to_thread(validate_mime_type, tmp_path, ext)
        except FileValidationError:
            tmp_path.unlink(missing_ok=True)
            raise

        # ── Step 4: Rename to final path ─────────────────────────────────────
        final_path = upload_dir / f"{file_hash[:16]}_{filename}"
        tmp_path.replace(final_path)

        # ── Step 5: Parse Document (offloaded — H6 Fix for Docling/OCR) ──────
        t_parse = time.perf_counter()
        parsed = await asyncio.to_thread(parse_document, final_path)
        parse_ms = (time.perf_counter() - t_parse) * 1000
        clean = clean_text(parsed.text)

        # ── Step 6: Extract Information (offloaded — H6 Fix) ─────────────────
        t_extract = time.perf_counter()

        def _run_extractors(text: str):
            contact = extract_contact(text)
            skills = extract_skills(text)
            exp_result = extract_experience(text)
            edu_entries = extract_education(text)
            cert_entries = extract_certifications(text)
            project_entries = extract_projects(text)
            summary = extract_summary(text)
            return contact, skills, exp_result, edu_entries, cert_entries, project_entries, summary

        contact, skills, exp_result, edu_entries, cert_entries, project_entries, summary = \
            await asyncio.to_thread(_run_extractors, clean)

        extract_ms = (time.perf_counter() - t_extract) * 1000

        logger.info(
            "Extraction complete: %d skills, %d exp, %d edu, %d certs, %d projects",
            len(skills), len(exp_result.entries), len(edu_entries),
            len(cert_entries), len(project_entries),
        )

        # ── Step 7: Persist Candidate ─────────────────────────────────────────
        effective_tenant_id = tenant_id or "default"
        resolved_name = (candidate_name or contact.name or None)
        resolved_email = (candidate_email or contact.email or None)
        resolved_phone = (candidate_phone or contact.phone or None)
        if isinstance(resolved_name, str):
            resolved_name = resolved_name.strip() or None
        if isinstance(resolved_email, str):
            resolved_email = resolved_email.strip().lower() or None
        if isinstance(resolved_phone, str):
            resolved_phone = resolved_phone.strip() or None

        candidate = await self._get_or_create_candidate(
            name=resolved_name,
            email=resolved_email,
            phone=resolved_phone,
            tenant_id=effective_tenant_id,
        )

        # ── Step 8: Persist Resume ────────────────────────────────────────────
        parsed_data = {
            "summary": summary,
            "skills": [s.normalized_name for s in skills],
            "experience_entries": len(exp_result.entries),
            "education_entries": len(edu_entries),
            "certifications": len(cert_entries),
            "projects": len(project_entries),
        }

        resume = Resume(
            tenant_id=effective_tenant_id,
            candidate_id=candidate.id,
            original_filename=filename,
            file_path=str(final_path),
            file_hash=file_hash,
            file_size_bytes=len(content),
            file_extension=ext,
            status="parsed",
            parse_source=parsed.source,
            raw_text=clean[:50000],
            parsed_json=json.dumps(parsed_data),
            parse_time_ms=round(parse_ms, 2),
            extraction_time_ms=round(extract_ms, 2),
        )
        resume = await self._resume_repo.create(resume)

        # ── Step 9: Persist Skills ────────────────────────────────────────────
        await self._persist_skills(candidate.id, skills, effective_tenant_id)

        # ── Step 9.5: Clean up old profile history to prevent duplication ──────
        from sqlalchemy import delete
        await self._session.execute(
            delete(Experience).where(Experience.candidate_id == candidate.id)
        )
        await self._session.execute(
            delete(Education).where(Education.candidate_id == candidate.id)
        )
        await self._session.execute(
            delete(Certification).where(Certification.candidate_id == candidate.id)
        )

        # ── Step 10: Persist Experience ───────────────────────────────────────
        for entry in exp_result.entries:
            exp = Experience(
                tenant_id=effective_tenant_id,
                candidate_id=candidate.id,
                company=entry.company,
                job_title=entry.job_title,
                start_date=entry.start_date,
                end_date=entry.end_date,
                is_current=entry.is_current,
                duration_months=entry.duration_months,
                raw_start_date=entry.raw_start_date,
                raw_end_date=entry.raw_end_date,
                description=entry.description,
            )
            self._session.add(exp)

        # ── Step 11: Persist Education ────────────────────────────────────────
        for edu in edu_entries:
            edu_model = Education(
                tenant_id=effective_tenant_id,
                candidate_id=candidate.id,
                degree=edu.degree,
                degree_normalized=edu.degree_normalized,
                institution=edu.institution,
                field_of_study=edu.field_of_study,
                graduation_year=edu.graduation_year,
                gpa=edu.gpa,
            )
            self._session.add(edu_model)

        # ── Step 12: Persist Certifications ──────────────────────────────────
        for cert in cert_entries:
            cert_model = Certification(
                tenant_id=effective_tenant_id,
                candidate_id=candidate.id,
                name=cert.name,
                issuer=cert.issuer,
                year=cert.year,
                credential_id=cert.credential_id,
            )
            self._session.add(cert_model)

        await self._session.flush()

        # ── Step 13: ATS Scoring (offloaded — H6 Fix) ────────────────────────
        t_score = time.perf_counter()
        scoring_input = ATSScoringInput(
            extracted_skills=[s.normalized_name for s in skills],
            total_experience_months=exp_result.total_months,
            education_entries=edu_entries,
            certification_entries=cert_entries,
            project_entries=project_entries,
        )
        # Resolve string job_profile to DB profile if possible
        resolved_profile = job_profile
        if isinstance(job_profile, str):
            from app.repositories.job_profile_repository import JobProfileRepository
            profile_repo = JobProfileRepository(self._session)
            db_profile = await profile_repo.get(job_profile, tenant_id)
            if not db_profile and tenant_id:
                db_profile = await profile_repo.get_default(tenant_id)
            if db_profile:
                resolved_profile = db_profile

        score_result = await asyncio.to_thread(compute_ats_score, scoring_input, resolved_profile)
        score_ms = (time.perf_counter() - t_score) * 1000

        ats_score = ATSScore(
            tenant_id=effective_tenant_id,
            resume_id=resume.id,
            skill_score=score_result.skill_score,
            experience_score=score_result.experience_score,
            education_score=score_result.education_score,
            certification_score=score_result.certification_score,
            project_score=score_result.project_score,
            total_score=score_result.total_score,
            recommendation=score_result.recommendation,
            total_experience_months=exp_result.total_months,
            matched_skills_count=len(score_result.skill_details.matched_required),
            missing_skills_count=len(score_result.skill_details.missing_required),
        )
        self._session.add(ats_score)

        # Update timing on resume
        resume.scoring_time_ms = round(score_ms, 2)
        await self._session.flush()

        total_ms = (time.perf_counter() - t_total) * 1000
        logger.info(
            "Resume '%s' fully processed in %.1f ms | Score=%.1f | %s",
            filename, total_ms, score_result.total_score, score_result.recommendation,
        )

        # Return with relations loaded
        return await self._resume_repo.get_with_relations(resume.id)  # type: ignore[return-value]

    async def get_resume(self, resume_id: str, tenant_id: str = None) -> Resume:
        """Fetch a resume with all relations eagerly loaded."""
        from app.core.exceptions import ResumeNotFoundError
        resume = await self._resume_repo.get_with_relations(resume_id, tenant_id=tenant_id)
        if not resume:
            raise ResumeNotFoundError(
                message=f"Resume '{resume_id}' not found.",
                details={"resume_id": resume_id},
            )
        return resume

    async def list_resumes(self, page: int = 1, page_size: int = 20, tenant_id: str = None) -> tuple[list[Resume], int]:
        """Return paginated list of resumes with total count."""
        offset = (page - 1) * page_size
        resumes = await self._resume_repo.get_all_with_relations(
            offset=offset, limit=page_size, tenant_id=tenant_id
        )
        total = await self._resume_repo.count(tenant_id=tenant_id)
        return list(resumes), total

    async def delete_resume(self, resume_id: str, tenant_id: str = None) -> None:
        """Delete a resume and its uploaded file."""
        from app.core.exceptions import ResumeNotFoundError
        resume = await self._resume_repo.get(resume_id, tenant_id=tenant_id)
        if not resume:
            raise ResumeNotFoundError(
                message=f"Resume '{resume_id}' not found.",
                details={"resume_id": resume_id},
            )
        # Delete file from disk
        file_path = Path(resume.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file: %s", file_path)

        await self._resume_repo.delete(resume)
        logger.info("Deleted resume record: %s", resume_id)

    async def _get_or_create_candidate(
        self,
        name: str | None,
        email: str | None,
        phone: str | None,
        tenant_id: str = "default",
    ) -> Candidate:
        """Return existing candidate by email, or create a new one."""
        if email:
            existing = await self._candidate_repo.get_by_email(email, tenant_id=tenant_id)
            if existing:
                if name and not existing.name:
                    existing.name = name
                if phone and not existing.phone:
                    existing.phone = phone
                await self._session.flush()
                return existing

        candidate = Candidate(tenant_id=tenant_id, name=name, email=email, phone=phone)
        return await self._candidate_repo.create(candidate)

    async def _persist_skills(
        self,
        candidate_id: str,
        skills: list,
        tenant_id: str = "default",
    ) -> None:
        """Upsert skills into the Skill master table and link to candidate."""
        from sqlalchemy import select

        for skill_obj in skills:
            # Get or create Skill master record
            result = await self._session.execute(
                select(Skill).where(Skill.normalized_name == skill_obj.normalized_name)
            )
            skill = result.scalar_one_or_none()
            if not skill:
                skill = Skill(
                    name=skill_obj.raw_name,
                    normalized_name=skill_obj.normalized_name,
                )
                self._session.add(skill)
                await self._session.flush()

            # Upsert CandidateSkill (skip if already exists)
            cs_result = await self._session.execute(
                select(CandidateSkill).where(
                    CandidateSkill.candidate_id == candidate_id,
                    CandidateSkill.skill_id == skill.id,
                    CandidateSkill.tenant_id == tenant_id,
                )
            )
            if not cs_result.scalar_one_or_none():
                candidate_skill = CandidateSkill(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    skill_id=skill.id,
                    source="resume",
                    confidence=skill_obj.confidence,
                )
                self._session.add(candidate_skill)
