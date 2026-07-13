"""
Education extractor.

Extracts degree, institution, field of study, and graduation year
from the education section of a resume.
Normalizes degrees using config/education_map.yaml.
"""
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz, process

from app.core.config import settings
from app.utils.text_cleaner import extract_section_text, remove_bullets

logger = logging.getLogger(__name__)

_EDUCATION_HEADERS = [
    "education", "academic background", "academic qualifications",
    "educational qualifications", "educational background", "academics",
]

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class EducationEntry:
    degree: Optional[str] = None
    degree_normalized: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None


@lru_cache(maxsize=1)
def _load_education_map() -> dict[str, list[str]]:
    """Load and cache the education normalization map."""
    config_path = Path(settings.education_map_path)
    if not config_path.exists():
        logger.warning("Education map not found at %s", config_path)
        return {}
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    result: dict[str, list[str]] = {}
    for normalized, data in raw.items():
        aliases = (data.get("aliases") or []) if isinstance(data, dict) else []
        result[normalized] = [normalized] + [a.lower() for a in aliases]
    return result


def _build_degree_index() -> dict[str, str]:
    """Build flat alias → normalized map."""
    edu_map = _load_education_map()
    index: dict[str, str] = {}
    for normalized, aliases in edu_map.items():
        for alias in aliases:
            index[alias.lower()] = normalized
    return index


_DEGREE_INDEX: Optional[dict[str, str]] = None


def _get_degree_index() -> dict[str, str]:
    global _DEGREE_INDEX
    if _DEGREE_INDEX is None:
        _DEGREE_INDEX = _build_degree_index()
    return _DEGREE_INDEX


def normalize_degree(raw: str) -> Optional[str]:
    """
    Map a raw degree string to its normalized code.

    Returns:
        Normalized code (e.g., "btech") or None if unrecognized.
    """
    index = _get_degree_index()
    raw_lower = raw.strip().lower()

    # Exact match
    if raw_lower in index:
        return index[raw_lower]

    # Word boundary match for all aliases
    all_aliases = list(index.keys())
    for alias in all_aliases:
        if _is_word_match(raw_lower, alias):
            return index[alias]

    # Fallback: fuzzy match only for long aliases (length >= 5) to allow minor typos
    long_aliases = [a for a in all_aliases if len(a) >= 5]
    if long_aliases:
        matches = process.extract(
            raw_lower,
            long_aliases,
            scorer=fuzz.partial_ratio,
            limit=1,
            score_cutoff=85,
        )
        if matches:
            alias = matches[0][0]
            return index[alias]

    return None


def extract_education(text: str) -> list[EducationEntry]:
    """
    Extract all education entries from resume text.

    Returns:
        List of EducationEntry objects.
    """
    section = extract_section_text(text, _EDUCATION_HEADERS)
    if not section:
        logger.debug("No education section found.")
        return []

    entries = _parse_education_section(section)
    logger.debug("Extracted %d education entries.", len(entries))
    return entries


def _parse_education_section(section: str) -> list[EducationEntry]:
    """
    Parse the education section into individual entries.

    Each entry typically spans 2-4 lines:
      Line 1: Degree + Field
      Line 2: Institution
      Line 3: Year / GPA
    """
    degree_index = _get_degree_index()
    all_degree_aliases = list(degree_index.keys())

    entries: list[EducationEntry] = []
    lines = [
        remove_bullets(line).strip()
        for line in section.split("\n")
        if line.strip()
    ]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line contains a recognizable degree keyword
        degree_raw, normalized = _find_degree_in_line(line, all_degree_aliases, degree_index)
        if degree_raw:
            entry = EducationEntry(degree=degree_raw, degree_normalized=normalized)

            # 1. Search backward for institution (up to 3 lines back)
            for j in range(i - 1, max(-1, i - 4), -1):
                prev_line = lines[j]
                prev_degree_raw, _ = _find_degree_in_line(prev_line, all_degree_aliases, degree_index)
                if prev_degree_raw:
                    break
                if re.search(r"\b(college|university|school|institute|academy|vidyalaya|polytechnic|international|global)\b", prev_line, re.IGNORECASE):
                    entry.institution = prev_line[:300]
                    break

            # 2. If not found backward, search ahead (up to 3 lines ahead)
            if not entry.institution:
                for j in range(i + 1, min(i + 4, len(lines))):
                    ahead = lines[j]
                    next_degree_raw, _ = _find_degree_in_line(ahead, all_degree_aliases, degree_index)
                    if next_degree_raw:
                        break
                    if re.search(r"\b(college|university|school|institute|academy|vidyalaya|polytechnic|international|global)\b", ahead, re.IGNORECASE):
                        entry.institution = ahead[:300]
                        break

            # 3. Fallback: if still no institution, pick the first non-degree, non-year, non-gpa line around i
            if not entry.institution:
                for j in range(i - 1, max(-1, i - 3), -1):
                    prev_line = lines[j]
                    prev_degree_raw, _ = _find_degree_in_line(prev_line, all_degree_aliases, degree_index)
                    if prev_degree_raw or _YEAR_RE.search(prev_line) or len(prev_line.split()) < 2:
                        break
                    entry.institution = prev_line[:300]
                    break
                if not entry.institution:
                    for j in range(i + 1, min(i + 3, len(lines))):
                        ahead = lines[j]
                        next_degree_raw, _ = _find_degree_in_line(ahead, all_degree_aliases, degree_index)
                        if next_degree_raw or _YEAR_RE.search(ahead) or len(ahead.split()) < 2:
                            break
                        entry.institution = ahead[:300]
                        break

            # 4. Search for graduation year and GPA/marks (scan a window around the degree line)
            for j in range(max(0, i - 3), min(len(lines), i + 4)):
                ahead = lines[j]
                year_match = _YEAR_RE.search(ahead)
                if year_match and not entry.graduation_year:
                    entry.graduation_year = int(year_match.group(0))
                gpa_match = re.search(r"(?:gpa|cgpa|grade|marks|percentage)[:\s]*([\d.]+(?:\s*%|\s*/\s*\d+)?)", ahead, re.IGNORECASE)
                if gpa_match and not entry.gpa:
                    entry.gpa = gpa_match.group(1)

            entries.append(entry)
            i += 1
        else:
            i += 1

    return entries


def _is_word_match(line: str, alias: str) -> bool:
    """Check if the alias is matched as a complete word/phrase boundary in the line."""
    escaped_alias = re.escape(alias)
    pattern = r"(?:^|[^a-zA-Z0-9])" + escaped_alias + r"(?:$|[^a-zA-Z0-9])"
    return bool(re.search(pattern, line))


def _find_degree_in_line(
    line: str,
    all_aliases: list[str],
    degree_index: dict[str, str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Detect if a line contains a degree keyword.

    Returns:
        (raw_degree_text, normalized_code) or (None, None)
    """
    line_lower = line.lower()

    # Reject if it looks like an institution name rather than a degree
    if re.search(r"\b(college|university|school|institute|academy|vidyalaya)\b", line_lower):
        # Allowed to be a degree only if it contains clear degree/diploma words
        if not re.search(r"\b(bachelor|master|doctor|phd|degree|diploma|associate|12th|10th|hsc|ssc|intermediate|matriculation|certificates?)\b", line_lower):
            return None, None

    # Word boundary match for all aliases
    for alias in all_aliases:
        if _is_word_match(line_lower, alias):
            return line, degree_index[alias]

    # Fallback: fuzzy match only for long aliases (length >= 5) to allow minor typos
    long_aliases = [a for a in all_aliases if len(a) >= 5]
    if long_aliases:
        matches = process.extract(
            line_lower,
            long_aliases,
            scorer=fuzz.partial_ratio,
            limit=1,
            score_cutoff=85,
        )
        if matches:
            alias = matches[0][0]
            return line, degree_index[alias]

    return None, None
