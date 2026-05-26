"""Static encyclopedia seed data loading."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DATA_ROOT = Path(__file__).resolve().parent / "data"
DEFAULT_USER_PREFERENCES_PATH = DATA_ROOT / "default-user-preferences.json"
SAFETY_RULES_PATH = DATA_ROOT / "safety-rules.json"
OFFICIAL_WEB_SOURCES_PATH = DATA_ROOT / "official-web-sources.json"
CORE_DEPENDENCY_SKILLS_PATH = DATA_ROOT / "core-dependency-skills.json"
SOURCE_FACTS_PATH = DATA_ROOT / "source-facts-seed.json"
TOPIC_DOSSIERS_PATH = DATA_ROOT / "topic-dossiers-seed.json"
EVIDENCE_RECORDS_PATH = DATA_ROOT / "evidence-records-seed.json"
GLOSSARY_TERMS_PATH = DATA_ROOT / "glossary-terms.json"
CONCEPT_DIRECTORY_PATH = DATA_ROOT / "concept-directory.json"
KNOWLEDGE_COVERAGE_REQUIREMENTS_PATH = DATA_ROOT / "knowledge-coverage-requirements.json"
LOCAL_SOURCE_CANDIDATES_PATH = DATA_ROOT / "local-source-candidates.json"
KNOWLEDGE_SOURCE_LABELS_PATH = DATA_ROOT / "knowledge-source-labels.json"
TOPIC_NARRATIVES_PATH = DATA_ROOT / "topic-narratives.json"
KNOWLEDGE_DISPLAY_OVERRIDES_PATH = DATA_ROOT / "knowledge-display-overrides.json"


def _load_dict(path: Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} data must be an object: {path}")
    return copy.deepcopy(payload)


def _load_list(path: Path, *, label: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{label} data must be a list: {path}")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"{label} item at index {index} is not an object")
        items.append(copy.deepcopy(item))
    return items


def load_derived_glossary_terms(path: Path = GLOSSARY_TERMS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="glossary terms")


def load_derived_concept_directory(path: Path = CONCEPT_DIRECTORY_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="concept directory")


def load_default_user_preferences(path: Path = DEFAULT_USER_PREFERENCES_PATH) -> dict[str, Any]:
    return _load_dict(path, label="default user preferences")


def load_safety_rules(path: Path = SAFETY_RULES_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="safety rules")


def load_official_web_sources(path: Path = OFFICIAL_WEB_SOURCES_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="official web sources")


def load_core_dependency_skills(path: Path = CORE_DEPENDENCY_SKILLS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="core dependency skills")


def load_derived_source_facts(path: Path = SOURCE_FACTS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="source facts")


def load_derived_topic_dossiers(path: Path = TOPIC_DOSSIERS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="topic dossiers")


def load_derived_evidence_records(path: Path = EVIDENCE_RECORDS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="evidence records")


def load_knowledge_coverage_requirements(path: Path = KNOWLEDGE_COVERAGE_REQUIREMENTS_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="knowledge coverage requirements")


def load_local_source_candidates(path: Path = LOCAL_SOURCE_CANDIDATES_PATH) -> list[dict[str, Any]]:
    return _load_list(path, label="local source candidates")


def load_knowledge_source_labels(path: Path = KNOWLEDGE_SOURCE_LABELS_PATH) -> dict[str, str]:
    payload = _load_dict(path, label="knowledge source labels")
    return {str(key): str(value) for key, value in payload.items()}


def load_knowledge_display_overrides(path: Path = KNOWLEDGE_DISPLAY_OVERRIDES_PATH) -> dict[str, Any]:
    return _load_dict(path, label="knowledge display overrides")


def load_topic_narratives(path: Path = TOPIC_NARRATIVES_PATH) -> dict[str, dict[str, str]]:
    payload = _load_dict(path, label="topic narratives")
    narratives: dict[str, dict[str, str]] = {}
    for key, value in payload.items():
        if not isinstance(value, dict):
            raise ValueError(f"topic narrative for {key} is not an object")
        narratives[str(key)] = {str(inner_key): str(inner_value) for inner_key, inner_value in value.items()}
    return narratives
