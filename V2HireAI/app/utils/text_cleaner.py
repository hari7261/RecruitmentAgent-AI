"""
Text cleaning utilities.

Normalizes raw text extracted from resumes for consistent downstream
processing by the NLP pipeline and extractors.
"""
import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Apply a full cleaning pipeline to raw resume text.

    Steps:
    1. Unescape HTML entities (e.g., &amp; -> &)
    2. Unicode normalize (NFKC)
    3. Remove markdown formatting (hashes, bold/italic symbols, HTML comments)
    4. Remove null bytes and control characters
    5. Normalize line endings
    6. Collapse excessive blank lines (max 2 consecutive)
    7. Strip trailing whitespace from each line
    8. Collapse multiple spaces to single space within lines
    """
    if not text:
        return ""

    import html

    # Decode HTML entities
    text = html.unescape(text)

    # 2. Unicode normalize
    text = unicodedata.normalize("NFKC", text)

    # Remove Docling XML/HTML-like comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove leading markdown header symbols on lines (e.g. "## Experience" -> "Experience")
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Remove bold/italic markdown markers (e.g. "**", "*", "__", "_")
    text = re.sub(r"(\*\*|__|\*|_)", "", text)

    # 3. Remove null bytes and non-printable control chars (keep \n \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 4. Normalize Windows/Mac line endings to Unix
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]

    # 6. Collapse 3+ consecutive blank lines → 2 blank lines
    cleaned_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            # Collapse multiple spaces within a line
            cleaned_lines.append(re.sub(r" {2,}", " ", line))

    return "\n".join(cleaned_lines).strip()


def extract_section_text(
    text: str,
    section_headers: list[str],
    next_section_headers: list[str] | None = None,
) -> str:
    """
    Extract text belonging to a specific resume section.

    Scans for any of the given `section_headers` (case-insensitive),
    then returns all text until the next known section header begins.

    Args:
        text: Full resume text.
        section_headers: Patterns that mark the START of the target section.
        next_section_headers: Patterns that mark the END (next section starts).
                              Defaults to a comprehensive list of common headers.

    Returns:
        Extracted section text, or empty string if section not found.
    """
    if next_section_headers is None:
        next_section_headers = _COMMON_SECTION_HEADERS

    # Build regex for section start
    start_pattern = re.compile(
        r"^\s*(?:" + "|".join(re.escape(h) for h in section_headers) + r")\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Build regex for section end (next section header)
    all_other_headers = [
        h for h in next_section_headers
        if not any(h.lower() == sh.lower() for sh in section_headers)
    ]
    end_pattern = re.compile(
        r"^\s*(?:" + "|".join(re.escape(h) for h in all_other_headers) + r")\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    start_match = start_pattern.search(text)
    if not start_match:
        return ""

    section_start = start_match.end()

    # Find next section
    end_match = end_pattern.search(text, section_start)
    section_end = end_match.start() if end_match else len(text)

    return text[section_start:section_end].strip()


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace sequences to a single space."""
    return re.sub(r"\s+", " ", text).strip()


def remove_bullets(text: str) -> str:
    """Remove bullet characters and list markers from the start of lines."""
    # Matches either a list number followed by a dot, parenthesis, or space (e.g., '1.', '2)', '3 '),
    # or leading spaces/bullet characters.
    return re.sub(r"^(\s*\d+[\.\)\s]\s*|[\s•\-\*\·◦▪▸►→\+]+)", "", text, flags=re.MULTILINE)


# ── Common resume section header names ────────────────────────────────────────
_COMMON_SECTION_HEADERS: list[str] = [
    "summary", "objective", "profile", "about me", "about",
    "experience", "work experience", "work history", "employment",
    "employment history", "professional experience", "work and research experience",
    "work & research experience", "research experience", "research & experience",
    "professional history", "relevant experience", "industry experience",
    "additional experience", "technical experience", "work and project experience",
    "work & project experience",
    "education", "academic background", "academic qualifications",
    "educational qualifications", "educational background", "academics",
    "skills", "technical skills", "core competencies", "competencies",
    "certifications", "licenses", "credentials", "certifications & licenses",
    "projects", "personal projects", "academic projects", "key projects",
    "achievements", "awards", "honors",
    "publications", "research",
    "languages", "hobbies", "interests", "references",
    "contact", "personal information", "personal details",
    "positions of responsibility", "positions of leadership", "leadership",
    "extra-curricular activities", "extracurricular activities",
    "volunteer experience", "volunteering",
]
