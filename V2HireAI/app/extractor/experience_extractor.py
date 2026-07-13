"""
Work experience extractor.

Extracts structured work history from resume text using:
- Section detection to isolate the experience block
- spaCy NER for ORG (company) and DATE entities
- Regex patterns for date ranges
- dateparser for robust date string parsing
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.utils.text_cleaner import extract_section_text, remove_bullets
from app.utils.date_utils import parse_date, is_present, calc_duration_months

logger = logging.getLogger(__name__)

_EXPERIENCE_HEADERS = [
    "experience", "work experience", "professional experience",
    "employment", "work history", "employment history",
    "career history", "career summary", "work and research experience",
    "work & research experience", "research experience", "professional history",
    "work and project experience", "work & project experience", "relevant experience",
]

# Matches date ranges like:
#   Jan 2020 – Dec 2022
#   January 2020 - Present
#   06/2019 - 03/2021
#   2019 - 2022
_DATE_RANGE_RE = re.compile(
    r"("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,]?\d{4}"
    r"|"
    r"\d{1,2}[/\-]\d{4}"  # 01/2020
    r"|"
    r"\d{4}"               # Year only
    r")"
    r"\s*[-–—to]+\s*"
    r"("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,]?\d{4}"
    r"|"
    r"\d{1,2}[/\-]\d{4}"
    r"|"
    r"\d{4}"
    r"|"
    r"Present|Current|Till Date|Ongoing|Now"
    r")",
    re.IGNORECASE,
)

# ── Job title keyword heuristics ───────────────────────────────────────────────
_TITLE_KEYWORDS = re.compile(
    r"\b(?:engineer|developer|analyst|manager|designer|architect|"
    r"consultant|specialist|lead|head|director|officer|intern|"
    r"associate|senior|junior|principal|staff|vp|cto|ceo|coo|"
    r"researcher|scholar|fellow|assistant|lecturer|scientist|member|"
    r"student|instructor|professor)\b",
    re.IGNORECASE,
)


@dataclass
class ExperienceEntry:
    company: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    duration_months: int = 0
    raw_start_date: Optional[str] = None
    raw_end_date: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ExperienceResult:
    entries: list[ExperienceEntry] = field(default_factory=list)
    total_months: int = 0
    current_company: Optional[str] = None


def extract_experience(text: str) -> ExperienceResult:
    """
    Extract all work experience entries from resume text.

    Returns:
        ExperienceResult with entries, total months, and current company.
    """
    section = extract_section_text(text, _EXPERIENCE_HEADERS)
    if not section:
        logger.debug("No experience section found.")
        return ExperienceResult()

    entries = _parse_experience_section(section)
    total_months = sum(e.duration_months for e in entries)
    current_company = next(
        (e.company for e in entries if e.is_current and e.company), None
    )

    logger.debug(
        "Extracted %d experience entries, %d total months.",
        len(entries), total_months,
    )
    return ExperienceResult(
        entries=entries,
        total_months=total_months,
        current_company=current_company,
    )


def _parse_experience_section(section_text: str) -> list[ExperienceEntry]:
    """
    Split the experience section into individual job entries and parse each.
    """
    # Split on date ranges — each date range likely starts a new entry
    parts = _DATE_RANGE_RE.split(section_text)

    entries: list[ExperienceEntry] = []
    i = 0
    while i + 2 < len(parts):
        chunk = parts[i]
        raw_start = parts[i + 1]
        raw_end = parts[i + 2]
        # The description is the next chunk (index i + 3) which also acts as the header chunk for the next entry
        description = parts[i + 3] if i + 3 < len(parts) else ""

        entry = _build_entry(chunk, raw_start, raw_end, description)
        if entry:
            entries.append(entry)

        i += 3

    # Deduplicate entries with same company+title
    return _deduplicate(entries)


def _build_entry(
    header_chunk: str,
    raw_start: str,
    raw_end: str,
    description: str,
) -> Optional[ExperienceEntry]:
    """Build a single ExperienceEntry from parsed chunks."""
    # Parse dates
    start_date = parse_date(raw_start.strip())
    current = is_present(raw_end.strip())
    end_date = None if current else parse_date(raw_end.strip())
    duration = calc_duration_months(start_date, end_date, is_current=current)

    # Extract company and title from the header chunk and succeeding description chunk
    company, title = _extract_company_title(header_chunk, description)

    if not company and not title and duration == 0:
        return None

    return ExperienceEntry(
        company=company,
        job_title=title,
        start_date=start_date,
        end_date=end_date,
        is_current=current,
        duration_months=duration,
        raw_start_date=raw_start.strip(),
        raw_end_date=raw_end.strip(),
        description=description.strip()[:500] if description else None,
    )


def _extract_company_title(chunk: str, next_chunk: str = "") -> tuple[Optional[str], Optional[str]]:
    """
    Attempt to extract company name and job title from text preceding and succeeding a date range.
    """
    # Helper to clean bracket metadata from candidate lines
    def clean_line(text: str) -> str:
        text = re.sub(r"\s*\[.*?\]", "", text)
        text = re.sub(r"\s*\(.*?\)", "", text)
        return text.strip()

    # 1. Parse preceding lines (scan bottom-up until we hit a bullet point of the previous job)
    lines_prev: list[str] = []
    for line in reversed(chunk.split("\n")):
        line_strip = line.strip()
        if not line_strip:
            continue
        if line_strip[0] in "•◦-▪▸►→*·" or line_strip == "•" or line_strip == "◦":
            break
        if line_strip.startswith("- ") or line_strip.startswith("* ") or line_strip.startswith("o "):
            break
        lines_prev.append(clean_line(remove_bullets(line_strip)))
        if len(lines_prev) >= 3:
            break
            
    lines_prev.reverse()

    # 2. Parse succeeding lines (scan top-down until we hit description details)
    lines_next: list[str] = []
    for line in next_chunk.split("\n"):
        line_strip = line.strip()
        if not line_strip:
            continue
        if line_strip[0] in "•◦-▪▸►→*·" or line_strip.startswith("- ") or line_strip.startswith("* ") or line_strip.startswith("o "):
            break
        lines_next.append(clean_line(remove_bullets(line_strip)))
        if len(lines_next) >= 2:
            break

    company: Optional[str] = None
    title: Optional[str] = None

    # Check lines_prev first (closest to dates)
    for line in reversed(lines_prev):
        if not line or len(line) < 3:
            continue
        
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                if not part:
                    continue
                if _TITLE_KEYWORDS.search(part) and not title:
                    title = part[:200]
                elif not company and len(part.split()) <= 8:
                    company = part[:200]
            continue

        if _TITLE_KEYWORDS.search(line) and not title:
            title = line[:200]
        elif not company and len(line.split()) <= 8:
            company = line[:200]

    # Check lines_next for missing info
    for line in lines_next:
        if not line or len(line) < 3:
            continue
            
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                if not part:
                    continue
                if _TITLE_KEYWORDS.search(part) and not title:
                    title = part[:200]
                elif not company and len(part.split()) <= 8:
                    if not _TITLE_KEYWORDS.search(part):
                        company = part[:200]
            continue

        if _TITLE_KEYWORDS.search(line) and not title:
            title = line[:200]
        elif not company and len(line.split()) <= 8:
            if not _TITLE_KEYWORDS.search(line):
                company = line[:200]

    # Shift logic: If company is None but we found a title in lines_prev and another title in lines_next
    if not company and title:
        next_title = None
        for line in lines_next:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                for part in parts:
                    if _TITLE_KEYWORDS.search(part):
                        next_title = part[:200]
                        break
                if next_title:
                    break
            elif _TITLE_KEYWORDS.search(line):
                next_title = line[:200]
                break
        if next_title and next_title != title:
            company = title
            title = next_title

    return company, title


def _deduplicate(entries: list[ExperienceEntry]) -> list[ExperienceEntry]:
    """Remove near-duplicate entries (same company + same start date)."""
    seen: set[tuple] = set()
    unique: list[ExperienceEntry] = []
    for e in entries:
        key = (e.company, e.start_date)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique
