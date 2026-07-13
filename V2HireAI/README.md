# Resume ATS Backend — Phase 1

A production-quality **Applicant Tracking System (ATS)** backend built with **Python / FastAPI**.  
Parses PDF and DOCX resumes using **Docling** (with EasyOCR fallback), extracts structured data via **spaCy** + **RapidFuzz**, and scores candidates using a fully **deterministic rule engine** — no LLMs, no AI.

---

## Technology Stack

| Layer | Library |
|---|---|
| Web Framework | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite / aiosqlite (Phase 1) |
| Migrations | Alembic (async) |
| Validation | Pydantic v2 |
| Document Parsing | Docling + docling-ibm-models |
| OCR Fallback | EasyOCR + pdf2image |
| NLP | spaCy (en_core_web_sm) |
| Fuzzy Matching | RapidFuzz |
| Date Parsing | dateparser |
| Config | pydantic-settings + PyYAML |

---

## Project Structure

```
resume_ats/
├── app/
│   ├── api/v1/endpoints/resume.py    # 5 REST endpoints
│   ├── core/                         # config, logging, exceptions
│   ├── database/                     # engine, session, base
│   ├── models/                       # 7 SQLAlchemy ORM models
│   ├── schemas/                      # Pydantic v2 response schemas
│   ├── repositories/                 # Generic async CRUD + specific repos
│   ├── services/                     # Orchestration (resume + ATS)
│   ├── parser/                       # Docling + EasyOCR fallback
│   ├── extractor/                    # 7 extractors (contact/skills/exp/edu/cert/proj/summary)
│   ├── matcher/                      # RapidFuzz skill matcher
│   ├── scorer/                       # 5 sub-scorers + orchestrator
│   └── utils/                        # file, date, text, hash utilities
├── config/
│   ├── skills_config.yaml            # 200+ tech skills with aliases
│   ├── education_map.yaml            # Degree normalization map
│   └── job_profile.yaml             # ATS scoring criteria (configurable)
├── migrations/                       # Alembic async migrations
├── tests/                            # pytest test suite
├── uploads/                          # Uploaded resume files
├── logs/                             # Rotating log files
├── alembic.ini
├── pyproject.toml
└── requirements.txt
```

---

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

# Install packages
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
# Copy the example env file
copy .env.example .env

# Edit .env as needed (DB URL, upload dir, file size limits, etc.)
```

### 3. Run Database Migrations

```bash
# Generate initial migration (first time only)
alembic revision --autogenerate -m "initial_schema"

# Apply migrations
alembic upgrade head
```

> **Note:** On first startup, the app also calls `init_db()` which auto-creates all tables.
> Alembic is preferred in production.

### 4. Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open API Docs

```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/resume/upload` | Upload PDF/DOCX, parse, score |
| `GET` | `/api/v1/resume` | Paginated list of resumes |
| `GET` | `/api/v1/resume/{id}` | Full resume detail |
| `GET` | `/api/v1/resume/{id}/score` | ATS score + recommendation |
| `DELETE` | `/api/v1/resume/{id}` | Delete resume + file |
| `GET` | `/health` | Health check |

### Example: Upload a Resume

```bash
curl -X POST http://localhost:8000/api/v1/resume/upload \
  -F "file=@/path/to/resume.pdf"
```

**Response:**
```json
{
  "resume_id": "abc123...",
  "candidate_id": "def456...",
  "status": "parsed",
  "message": "Resume uploaded, parsed, and scored successfully.",
  "candidate": {
    "id": "def456...",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1-555-123-4567"
  },
  "ats_score": {
    "total_score": 82.5,
    "recommendation": "Hire",
    "skill_score": 34.0,
    "experience_score": 28.0,
    "education_score": 10.0,
    "certification_score": 7.5,
    "project_score": 3.0
  }
}
```

---

## ATS Scoring

All scoring is **deterministic** — no LLMs, no AI.

| Component | Weight | Criteria |
|---|---|---|
| Skills | 40% | Required (70%) + Preferred (30%) match via RapidFuzz |
| Experience | 30% | Linear interpolation between min_years and preferred_years |
| Education | 10% | Normalized degree vs. preferred list |
| Certifications | 10% | Required (7pt) + Preferred (3pt) pattern match |
| Projects | 10% | Project count vs. min/preferred thresholds |

### Hiring Recommendations

| Score | Recommendation |
|---|---|
| 90 – 100 | **Strong Hire** |
| 75 – 89 | **Hire** |
| 60 – 74 | **Review** |
| < 60 | **Reject** |

> Thresholds are configurable via `.env` (`STRONG_HIRE_THRESHOLD`, `HIRE_THRESHOLD`, `REVIEW_THRESHOLD`).

---

## Customizing Scoring Criteria

Edit `config/job_profile.yaml` to change what the ATS looks for — **no code changes required**:

```yaml
required_skills: [python, fastapi, sql, git]
preferred_skills: [docker, redis, aws, react]
min_experience_years: 2
preferred_experience_years: 5
preferred_education: [btech, mtech, msc]
preferred_certifications: [aws, azure, kubernetes]
```

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_upload.py -v
pytest tests/test_parser.py -v
pytest tests/test_scorer.py -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Migrating to PostgreSQL

Phase 1 uses SQLite for simplicity. To migrate:

1. Change `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/resume_ats
   ```
2. Install asyncpg: `pip install asyncpg`
3. Run: `alembic upgrade head`

No Python code changes required.

---

## Error Codes

| Code | HTTP | Description |
|---|---|---|
| `INVALID_FILE_TYPE` | 400 | Extension/MIME not allowed |
| `FILE_SIZE_EXCEEDED` | 400 | File larger than MAX_FILE_SIZE_MB |
| `DUPLICATE_RESUME` | 409 | Same file already uploaded (SHA-256 match) |
| `PARSE_ERROR` | 422 | Both Docling and OCR failed |
| `RESUME_NOT_FOUND` | 404 | Resume ID not in database |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Logs

Structured logs are written to `logs/ats.log` with rotation (10 MB × 5 backups).

Each upload logs:
- Upload event with filename and size
- Parse time (ms) and source (docling/ocr)
- Extraction summary (skill/exp/edu/cert/project counts)
- ATS score and recommendation
- Total processing time

---

## Phase 2 Roadmap

- [ ] PostgreSQL migration
- [ ] Redis caching for job profiles
- [ ] Celery async processing queue
- [ ] Multiple job profiles (`POST /job`)
- [ ] Elasticsearch full-text search
- [ ] Candidate comparison dashboard
- [ ] Bulk upload API
