from __future__ import annotations

import re

from src.domain.entities import SkillResult, UserInput
from src.domain.ports import Skill


class SpellingSkill(Skill):
    name = "spelling_skill"
    supported_modes = ("spelling",)

    def execute(self, user_input: UserInput) -> SkillResult:
        normalized_tokens = _normalize_tokens(user_input.content)
        normalized = " ".join(normalized_tokens)
        word = "".join(normalized_tokens)
        difficulty = user_input.context.get("difficulty_level", "B1")
        feedback = _build_feedback(word, difficulty)
        return SkillResult(
            content=normalized,
            metadata={
                "feedback": feedback,
                "mode": user_input.mode,
                "target_word": word,
                "letter_count": str(len(normalized_tokens)),
            },
        )


def build() -> SpellingSkill:
    return SpellingSkill()


def _normalize_tokens(text: str) -> list[str]:
    cleaned = text.lower()
    cleaned = cleaned.replace("-", " ")
    cleaned = cleaned.replace(",", " ")
    cleaned = cleaned.replace(".", " ")
    cleaned = cleaned.replace("letter", " ")
    cleaned = cleaned.replace("letters", " ")
    cleaned = cleaned.replace("spell", " ")
    tokens = re.findall(r"[a-z]", cleaned)
    return tokens if tokens else text.strip().split()


def _build_feedback(word: str, difficulty: str) -> str:
    if not word:
        return "No recognizable letters found."
    if difficulty in {"A2", "B1"}:
        return f"The word spells '{word}'. Say each letter clearly and pause slightly."
    return f"Recognized word: '{word}'. Practice smoother pacing and chunking."
