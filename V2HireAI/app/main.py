"""
FastAPI application factory.

Startup/shutdown lifecycle:
  - Configure logging
  - Initialize database tables
  - Register global exception handlers
  - Mount all routers
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import ATSBaseException
from app.core.logging_config import configure_logging

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── Router Imports ─────────────────────────────────────────────────────────────
from app.api.v1.endpoints.resume import router as resume_router
from app.api.v1.endpoints import auth, openings, applications, profiles, users, public, admin
from app.api.v1.endpoints import analytics, export as export_endpoints, candidate

# Configure logging before anything else
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    logger.info("═══ AI Recruitment Platform starting up ═══")
    logger.info("DB: %s", settings.database_url)
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig
        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied.")
    except Exception as exc:
        logger.error("Alembic migration failed: %s", exc)
        raise RuntimeError(
            f"Database migration failed: {exc}. Run 'alembic upgrade head' to repair the schema."
        ) from exc
    yield
    logger.info("═══ AI Recruitment Platform shut down ═══")


# ── App Instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multi-tenant AI Recruitment Platform. "
        "Organizations create job openings, candidates apply, "
        "and the system auto-parses resumes and scores candidates with ATS engine."
    ),
    openapi_tags=[
        {"name": "Public Portal", "description": "Unauthenticated endpoints for candidates."},
        {"name": "Auth", "description": "Authentication and token management."},
        {"name": "Admin", "description": "Super Admin platform management."},
        {"name": "Openings", "description": "Job posting CRUD (authenticated)."},
        {"name": "Applications", "description": "Candidate application management."},
        {"name": "Job Profiles", "description": "ATS scoring configuration."},
        {"name": "Users", "description": "Organization user management."},
        {"name": "Resume", "description": "Legacy resume upload and scoring."},
        {"name": "Analytics", "description": "Platform and org analytics."},
        {"name": "Export", "description": "CSV export endpoints."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000
    msg = f"HTTP {request.method} {request.url.path} - Status: {response.status_code} - {duration:.2f}ms"
    logger.info(msg)
    print(msg, flush=True)
    return response


# ── Global Exception Handlers ─────────────────────────────────────────────────

@app.exception_handler(ATSBaseException)
async def ats_exception_handler(request: Request, exc: ATSBaseException) -> JSONResponse:
    logger.warning(
        "ATS exception [%s] on %s %s: %s",
        exc.error_code, request.method, request.url.path, exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(public.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(openings.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(export_endpoints.router, prefix="/api/v1")
app.include_router(candidate.router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")


# ── Static Files ──────────────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "public_portal": "/portal",
    }

