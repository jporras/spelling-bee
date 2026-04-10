from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re


@dataclass(slots=True)
class TalkExercise:
    phrase: str
    level: str


class TalkPracticeManager:
    def __init__(self) -> None:
        self._active_sessions: dict[str, TalkExercise] = {}
        self._phrase_index_by_level = {"A2": 0, "B1": 0, "B2": 0, "C1": 0}
        self._phrases_by_level = {
            "A2": (
                "I like apples.",
                "She is my friend.",
                "We go to school by bus.",
            ),
            "B1": (
                "I would like a cup of tea, please.",
                "My brother usually walks to work in the morning.",
                "We visited the museum because the weather was rainy.",
            ),
            "B2": (
                "Could you tell me where the train station is?",
                "I decided to stay home because I needed to finish my report.",
                "She enjoys learning languages because it helps her travel with confidence.",
            ),
            "C1": (
                "Although the meeting was delayed, the team still managed to present a convincing proposal.",
                "If I had prepared earlier, I would have felt far more confident during the interview.",
                "The documentary was so engaging that we discussed its main ideas for nearly an hour afterward.",
            ),
        }

    def current(self, user_id: str) -> TalkExercise | None:
        return self._active_sessions.get(user_id)

    def start(self, user_id: str, level: str = "B1") -> TalkExercise:
        normalized_level = _normalize_level(level)
        phrases = self._phrases_by_level[normalized_level]
        index = self._phrase_index_by_level[normalized_level] % len(phrases)
        phrase = phrases[index]
        self._phrase_index_by_level[normalized_level] += 1
        exercise = TalkExercise(phrase=phrase, level=normalized_level)
        self._active_sessions[user_id] = exercise
        return exercise

    def restart(self, user_id: str, level: str = "B1") -> TalkExercise:
        current = self.current(user_id)
        if current is not None:
            return current
        return self.start(user_id, level=level)

    def clear(self, user_id: str) -> None:
        self._active_sessions.pop(user_id, None)

    def evaluate(self, user_id: str, attempt: str) -> dict[str, object]:
        exercise = self.current(user_id)
        if exercise is None:
            return {
                "score": 0.0,
                "feedback": "There is no active talk phrase yet.",
                "target_phrase": "",
                "transcript": attempt,
            }

        normalized_target = _normalize_phrase(exercise.phrase)
        normalized_attempt = _normalize_phrase(attempt)
        score = SequenceMatcher(None, normalized_target, normalized_attempt).ratio()
        if score >= 0.92:
            feedback = "Very good pronunciation match. You can retry to sound smoother or ask for a new phrase."
        elif score >= 0.72:
            feedback = "Good attempt. Some words may need clearer pronunciation. You can retry or ask for a new phrase."
        else:
            feedback = "Your attempt was quite different from the target phrase. Try again and focus on each word carefully."
        return {
            "score": round(score, 2),
            "feedback": feedback,
            "target_phrase": exercise.phrase,
            "transcript": attempt,
            "level": exercise.level,
        }


@dataclass(slots=True)
class SpellSession:
    words: list[str]
    index: int
    level: str
    awaiting_retry_decision: bool = False

    @property
    def current_word(self) -> str:
        return self.words[self.index]


class SpellPracticeManager:
    def __init__(self) -> None:
        self._active_sessions: dict[str, SpellSession] = {}
        self._proposal_index_by_level = {"A2": 0, "B1": 0, "B2": 0, "C1": 0}
        self._proposed_words_by_level = {
            "A2": ("cat", "book", "fish", "tree", "milk"),
            "B1": ("apple", "window", "planet", "school", "garden"),
            "B2": ("journey", "language", "sunlight", "backpack", "kitchen"),
            "C1": ("knowledge", "thoughtful", "architecture", "opportunity", "development"),
        }

    def current(self, user_id: str) -> SpellSession | None:
        return self._active_sessions.get(user_id)

    def start_from_choice(
        self,
        user_id: str,
        content: str,
        level: str = "B1",
        used_words: list[str] | None = None,
    ) -> SpellSession:
        normalized_level = _normalize_level(level)
        words = _parse_word_list(content)
        if not words:
            words = [self._next_proposed_word(normalized_level, used_words or [])]
        session = SpellSession(words=words, index=0, level=normalized_level)
        self._active_sessions[user_id] = session
        return session

    def evaluate_spelling(self, user_id: str, spelled_text: str) -> dict[str, object]:
        session = self.current(user_id)
        if session is None:
            return {
                "is_correct": False,
                "feedback": "There is no active spelling word yet.",
                "target_word": "",
                "recognized_word": "",
            }
        recognized = "".join(re.findall(r"[a-z]", spelled_text.lower()))
        target = session.current_word.lower()
        is_correct = recognized == target
        feedback = (
            f"Correct. You spelled '{target}' well."
            if is_correct
            else f"Not yet. I heard '{recognized or 'nothing clear'}', but the target word is '{target}'."
        )
        session.awaiting_retry_decision = True
        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "target_word": target,
            "recognized_word": recognized,
            "has_next_word": session.index < len(session.words) - 1,
        }

    def handle_followup(
        self,
        user_id: str,
        decision: str,
        used_words: list[str] | None = None,
    ) -> dict[str, object]:
        session = self.current(user_id)
        if session is None:
            return {
                "status": "missing",
                "message": "There is no active spelling session.",
            }

        lowered = decision.lower()
        if any(token in lowered for token in ("retry", "again", "otra vez", "reintentar")):
            session.awaiting_retry_decision = False
            return {
                "status": "retry",
                "message": f"Try spelling '{session.current_word}' again.",
                "target_word": session.current_word,
            }

        if session.index < len(session.words) - 1:
            session.index += 1
            session.awaiting_retry_decision = False
            return {
                "status": "next",
                "message": f"Great. Now spell '{session.current_word}'.",
                "target_word": session.current_word,
            }

        self._active_sessions.pop(user_id, None)
        normalized_level = session.level
        next_word = self._next_proposed_word(normalized_level, used_words or [])
        self._active_sessions[user_id] = SpellSession(words=[next_word], index=0, level=normalized_level)
        return {
            "status": "fresh",
            "message": f"That list is finished. A new suggested word is '{next_word}'. Spell it if you want to continue.",
            "target_word": next_word,
        }

    def _next_proposed_word(self, level: str, used_words: list[str]) -> str:
        proposed_words = self._proposed_words_by_level[level]
        normalized_used = {word.strip().lower() for word in used_words if word.strip()}
        for _ in range(len(proposed_words)):
            index = self._proposal_index_by_level[level] % len(proposed_words)
            candidate = proposed_words[index]
            self._proposal_index_by_level[level] += 1
            if candidate.lower() not in normalized_used:
                return candidate
        index = self._proposal_index_by_level[level] % len(proposed_words)
        candidate = proposed_words[index]
        self._proposal_index_by_level[level] += 1
        return candidate


def _normalize_phrase(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def _normalize_level(level: str) -> str:
    return level if level in {"A2", "B1", "B2", "C1"} else "B1"


def _parse_word_list(text: str) -> list[str]:
    lowered = text.strip().lower()
    if any(token in lowered for token in ("propose", "suggest", "imagine", "invent", "proponga", "propone", "inventa")):
        return []
    candidates = [token.strip().lower() for token in re.split(r"[,;\n]+", text) if token.strip()]
    if len(candidates) == 1 and " " in candidates[0]:
        words = [token for token in re.findall(r"[a-zA-Z]+", candidates[0])]
        return words if words else []
    return [re.sub(r"[^a-z]", "", word) for word in candidates if re.sub(r"[^a-z]", "", word)]
