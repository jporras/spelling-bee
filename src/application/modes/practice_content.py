from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LEVELS = ("A2", "B1", "B2", "C1")


@dataclass(frozen=True, slots=True)
class PracticeContent:
    talk_phrases: dict[str, tuple[str, ...]]
    listening_exercises: dict[str, tuple[dict[str, object], ...]]
    spelling_words: dict[str, tuple[str, ...]]


def load_practice_content(path: Path | None = None) -> PracticeContent:
    content_path = path or _default_content_path()
    raw = json.loads(content_path.read_text(encoding="utf-8"))
    return PracticeContent(
        talk_phrases=_read_level_tuple(raw, "talk_phrases"),
        listening_exercises=_read_listening_exercises(raw),
        spelling_words=_read_level_tuple(raw, "spelling_words"),
    )


def _default_content_path() -> Path:
    return Path(__file__).resolve().parents[3] / "prompts" / "skills" / "practice_content.json"


def _read_level_tuple(raw: dict[str, Any], key: str) -> dict[str, tuple[str, ...]]:
    section = raw.get(key, {})
    if not isinstance(section, dict):
        raise ValueError(f"Practice content section '{key}' must be an object.")
    loaded: dict[str, tuple[str, ...]] = {}
    for level in LEVELS:
        values = section.get(level, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Practice content section '{key}.{level}' must be a string list.")
        if not values:
            raise ValueError(f"Practice content section '{key}.{level}' cannot be empty.")
        loaded[level] = tuple(values)
    return loaded


def _read_listening_exercises(raw: dict[str, Any]) -> dict[str, tuple[dict[str, object], ...]]:
    section = raw.get("listening_exercises", {})
    if not isinstance(section, dict):
        raise ValueError("Practice content section 'listening_exercises' must be an object.")
    loaded: dict[str, tuple[dict[str, object], ...]] = {}
    required = {"id", "passage", "question", "expected_keywords", "answer_hint"}
    for level in LEVELS:
        exercises = section.get(level, [])
        if not isinstance(exercises, list) or not exercises:
            raise ValueError(f"Practice content section 'listening_exercises.{level}' cannot be empty.")
        normalized = []
        for exercise in exercises:
            if not isinstance(exercise, dict) or not required.issubset(exercise):
                raise ValueError(f"Listening exercise in level '{level}' is missing required fields.")
            keywords = exercise["expected_keywords"]
            if not isinstance(keywords, list) or not all(isinstance(value, str) for value in keywords):
                raise ValueError(f"Listening exercise '{exercise.get('id', level)}' has invalid keywords.")
            normalized.append(dict(exercise))
        loaded[level] = tuple(normalized)
    return loaded
