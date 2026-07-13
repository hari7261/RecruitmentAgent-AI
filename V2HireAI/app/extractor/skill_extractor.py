"""
Skill extractor with normalization.

Strategy:
1. Load the skills dictionary from config/skills_config.yaml.
2. For each skill and its aliases, perform case-insensitive substring search.
3. Additionally, use RapidFuzz fuzzy matching against all known terms.
4. Return deduplicated list of NormalizedSkill results.
"""
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import process, fuzz

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NormalizedSkill:
    """A skill as extracted and normalized from resume text."""
    raw_name: str           # What appeared in the text
    normalized_name: str    # Key from skills_config.yaml
    confidence: float = 1.0  # 0.0 - 1.0


@lru_cache(maxsize=1)
def _load_skills_config() -> dict[str, list[str]]:
    """
    Load and cache skills dictionary.

    Returns:
        {normalized_name: [alias1, alias2, ...]}
    """
    config_path = Path(settings.skills_config_path)
    if not config_path.exists():
        logger.warning("Skills config not found at %s", config_path)
        return {}
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    result: dict[str, list[str]] = {}
    for normalized, data in raw.items():
        aliases = (data.get("aliases") or []) if isinstance(data, dict) else []
        result[normalized] = [normalized] + [a.lower() for a in aliases]
    logger.info("Loaded %d skills from config.", len(result))
    return result


def _build_alias_index() -> dict[str, str]:
    """
    Build a flat {alias_lower: normalized_name} lookup index.
    Includes the normalized name itself as an alias.
    """
    skills = _load_skills_config()
    index: dict[str, str] = {}
    for normalized, aliases in skills.items():
        for alias in aliases:
            index[alias.lower()] = normalized
    return index


# Module-level alias index (built once on first import)
_ALIAS_INDEX: Optional[dict[str, str]] = None


def _get_alias_index() -> dict[str, str]:
    global _ALIAS_INDEX
    if _ALIAS_INDEX is None:
        _ALIAS_INDEX = _build_alias_index()
    return _ALIAS_INDEX


def extract_skills(text: str) -> list[NormalizedSkill]:
    """
    Extract and normalize skills from resume text.

    Combines exact/substring matching + RapidFuzz fuzzy matching.

    Args:
        text: Cleaned resume text (full document or skills section).

    Returns:
        Deduplicated list of NormalizedSkill objects.
    """
    alias_index = _get_alias_index()
    found: dict[str, NormalizedSkill] = {}  # normalized_name → best match

    text_lower = text.lower()

    # ── Pass 1: Exact / substring match ────────────────────────────────────
    for alias, normalized in alias_index.items():
        # M4 Fix: Short aliases (≤2 chars) need case-sensitive word boundary matching
        if len(alias) <= 2:
            pattern = r"(?<![a-zA-Z0-9_\-])" + re.escape(alias) + r"(?![a-zA-Z0-9_\-])"
            if re.search(pattern, text):  # case-sensitive on original text
                if normalized not in found or found[normalized].confidence < 1.0:
                    found[normalized] = NormalizedSkill(
                        raw_name=alias,
                        normalized_name=normalized,
                        confidence=1.0,
                    )
        else:
            # Word-boundary-aware search: avoid "node" matching "node_modules"
            pattern = r"(?<![a-z0-9_\-])" + re.escape(alias) + r"(?![a-z0-9_\-])"
            if re.search(pattern, text_lower):
                if normalized not in found or found[normalized].confidence < 1.0:
                    found[normalized] = NormalizedSkill(
                        raw_name=alias,
                        normalized_name=normalized,
                        confidence=1.0,
                    )

    # ── Pass 2: Fuzzy match on individual words/tokens ─────────────────────
    threshold = settings.fuzzy_match_threshold
    all_aliases = list(alias_index.keys())

    # Extract meaningful tokens from text (skip very short/common words)
    tokens = set(
        tok.lower()
        for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9._+#\-]{2,}", text)
    )

    for token in tokens:
        if token in alias_index:
            continue  # Already matched exactly above
        matches = process.extract(
            token,
            all_aliases,
            scorer=fuzz.token_sort_ratio,
            limit=1,
            score_cutoff=threshold,
        )
        for matched_alias, score, _ in matches:
            normalized = alias_index[matched_alias]
            confidence = score / 100.0
            if normalized not in found or found[normalized].confidence < confidence:
                found[normalized] = NormalizedSkill(
                    raw_name=token,
                    normalized_name=normalized,
                    confidence=confidence,
                )

    result = sorted(found.values(), key=lambda s: s.normalized_name)
    logger.debug("Extracted %d skills.", len(result))
    return result


def normalize_skill_name(raw: str) -> Optional[str]:
    """
    Normalize a single skill name to its canonical form.

    Returns the normalized key if found, else None.
    """
    alias_index = _get_alias_index()
    raw_lower = raw.strip().lower()
    if raw_lower in alias_index:
        return alias_index[raw_lower]
    # Try fuzzy
    matches = process.extract(
        raw_lower,
        list(alias_index.keys()),
        scorer=fuzz.token_sort_ratio,
        limit=1,
        score_cutoff=settings.fuzzy_match_threshold,
    )
    if matches:
        return alias_index[matches[0][0]]
    return None
