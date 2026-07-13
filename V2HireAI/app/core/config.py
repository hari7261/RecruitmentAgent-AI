# Application configuration using Pydantic Settings.
# All values are read from environment variables or a .env file.
import json
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    app_name: str = Field(default="AI Recruitment Platform")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    database_url: str = Field(default="sqlite+aiosqlite:///./recruitment_platform.db")
    upload_dir: str = Field(default="uploads")
    max_file_size_mb: int = Field(default=10)
    allowed_extensions_raw: str = Field(default="pdf,docx", alias="ALLOWED_EXTENSIONS", validation_alias="ALLOWED_EXTENSIONS")
    spacy_model: str = Field(default="en_core_web_sm")
    skills_config_path: str = Field(default="config/skills_config.yaml")
    education_map_path: str = Field(default="config/education_map.yaml")
    job_profile_path: str = Field(default="config/job_profile.yaml")
    strong_hire_threshold: int = Field(default=90)
    hire_threshold: int = Field(default=75)
    review_threshold: int = Field(default=60)
    fuzzy_match_threshold: int = Field(default=85)
    # Auth / JWT - CRITICAL: No default secret, must be set via SECRET_KEY env var
    # Will reject the known insecure default from .env.example
    secret_key: str = Field(min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)
    cors_origins_raw: str = Field(default="http://localhost:3000,http://localhost:5173", alias="CORS_ORIGINS")
    platform_name: str = Field(default="AI Recruitment Platform")
    platform_support_email: str = Field(default="support@example.com")
    default_plan: str = Field(default="starter")
    free_trial_resumes: int = Field(default=5)
    access_cookie_name: str = Field(default="access_token")
    refresh_cookie_name: str = Field(default="refresh_token")
    candidate_access_cookie_name: str = Field(default="candidate_access_token")
    candidate_refresh_cookie_name: str = Field(default="candidate_refresh_token")
    auth_cookie_secure: bool = Field(default=False)
    auth_cookie_samesite: str = Field(default="lax")
    @property
    def allowed_extensions(self) -> List[str]:
        raw = (self.allowed_extensions_raw or "pdf,docx").strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                return [str(e).strip().lower() for e in parsed if e]
            except json.JSONDecodeError:
                pass
        return [e.strip().lower() for e in raw.split(",") if e.strip()]
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    @property
    def cors_origins(self) -> list[str]:
        raw = (self.cors_origins_raw or "http://localhost:3000,http://localhost:5173").strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                return [str(e).strip() for e in parsed if e]
            except json.JSONDecodeError:
                pass
        return [e.strip() for e in raw.split(",") if e.strip()]

# Singleton settings instance
settings = Settings()

# S1 Fix: Validate secret key is not the insecure default
INSECURE_DEFAULTS = [
    "CHANGE_ME_SUPER_SECRET_KEY_2025_RECRUITMENT",
    "changeme",
    "secret",
    "secretkey",
]
if settings.secret_key in INSECURE_DEFAULTS:
    raise ValueError(
        f"SECURITY ERROR: SECRET_KEY is set to a known insecure value. "
        f"Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

