"""
Project extractor.

Extracts project entries from the PROJECTS section of a resume,
including project name, description, and technologies used
(cross-referenced against the skills dictionary).
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.utils.text_cleaner import extract_section_text, remove_bullets
from app.extractor.skill_extractor import extract_skills, NormalizedSkill

logger = logging.getLogger(__name__)

_PROJECT_HEADERS = [
    "projects", "personal projects", "academic projects",
    "key projects", "notable projects", "project experience",
    "portfolio", "selected projects", "technical projects",
    "academic & personal projects",
]

# Tech stack keywords often used in project descriptions
_TECH_INTRO = re.compile(
    r"(?:technologies?|tech stack|built with|tools?|languages?|frameworks?)"
    r"[:\s]+(.+?)(?:\.|$)",
    re.IGNORECASE,
)


@dataclass
class ProjectEntry:
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: list[str] = field(default_factory=list)


def extract_projects(text: str) -> list[ProjectEntry]:
    """
    Extract project entries from resume text.

    Returns:
        List of ProjectEntry objects with name, description, technologies.
    """
    section = extract_section_text(text, _PROJECT_HEADERS)
    if not section:
        logger.debug("No projects section found.")
        return []

    entries = _parse_project_section(section)
    logger.debug("Extracted %d projects.", len(entries))
    return entries


def _parse_project_section(section: str) -> list[ProjectEntry]:
    """
    Split the projects section by project boundaries.
    """
    entries: list[ProjectEntry] = []
    current_name: Optional[str] = None
    current_lines: list[str] = []
    
    # Track bullet markers
    next_line_is_title = False
    
    for line in section.split("\n"):
        line_raw = line.strip()
        if not line_raw:
            continue
            
        # Check if this line is just a bullet point separator
        if line_raw in ("•", "◦", "*", "-", "▪", "▸", "►", "→", "·"):
            # Save current project before starting new one
            if current_name and current_lines:
                entries.append(_build_project(current_name, current_lines))
                current_name = None
                current_lines = []
            next_line_is_title = True
            continue
            
        # If the line starts with a project bullet
        if line_raw.startswith(("• ", "* ", "▪ ", "▸ ", "► ", "→ ")):
            if current_name and current_lines:
                entries.append(_build_project(current_name, current_lines))
                current_name = None
                current_lines = []
            stripped = remove_bullets(line_raw).strip()
            current_name = stripped[:200]
            next_line_is_title = False
            continue
            
        stripped = remove_bullets(line_raw).strip()
        if not stripped:
            continue
            
        if next_line_is_title:
            current_name = stripped[:200]
            next_line_is_title = False
            continue
            
        # Heuristic title detection (if not marked by bullets)
        words = stripped.split()
        is_heuristic_title = (
            (stripped.endswith(":") or (len(words) <= 12 and all(w[0].isupper() for w in words if w.isalpha())))
            and not line_raw.startswith(("◦", "- ", "  -"))
        )
        
        if is_heuristic_title and current_name is None:
            current_name = stripped[:200]
        elif is_heuristic_title and current_name and current_lines:
            # End current project and start new one
            entries.append(_build_project(current_name, current_lines))
            current_name = stripped[:200]
            current_lines = []
        else:
            current_lines.append(stripped)
            
    # Flush last entry
    if current_name:
        entries.append(_build_project(current_name, current_lines))
        
    return entries[:15]


def _build_project(name: str, lines: list[str]) -> ProjectEntry:
    """Assemble a ProjectEntry from the collected lines."""
    description = " ".join(lines)[:1000]

    # Extract technologies from both name and description
    combined_text = f"{name} {description}"
    tech_skills = extract_skills(combined_text)
    tech_names = [s.normalized_name for s in tech_skills]

    return ProjectEntry(
        name=name,
        description=description or None,
        technologies=tech_names,
    )
