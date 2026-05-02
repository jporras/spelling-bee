from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from src.application.modes.grammar_mode import profile_to_metadata
from src.application.modes.practice_content import PracticeContent, load_practice_content
from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


@dataclass(slots=True)
class TalkExercise:
    phrase: str
    level: str


class TalkPracticeManager:
    def __init__(self, practice_content: PracticeContent | None = None) -> None:
        practice_content = practice_content or load_practice_content()
        self._active_sessions: dict[str, TalkExercise] = {}
        self._phrase_index_by_level = {"A2": 0, "B1": 0, "B2": 0, "C1": 0}
        self._phrases_by_level = practice_content.talk_phrases

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


class TalkModeWorkflow:
    def __init__(self, manager: TalkPracticeManager, memory) -> None:
        self._manager = manager
        self._memory = memory

    def handle(self, content: str, user_id: str, profile: UserProfile, source: str) -> OrchestrationResult:
        current = self._manager.current(user_id)
        lowered = content.lower().strip()
        if current is None or lowered in {"new", "new phrase", "nueva", "nueva frase"}:
            exercise = self._manager.start(user_id, level=profile.difficulty_level)
            return OrchestrationResult(
                selected_mode="free",
                final_text=f"Repeat this phrase:\n\n{exercise.phrase}",
                steps=[AgentStep("supervisor", "Orion", "free", "completed", "Supervisor started a pronunciation phrase.", exercise.phrase)],
                metadata={
                    "selected_agent": "conversation",
                    "speak_after_display": exercise.phrase,
                    "target_phrase": exercise.phrase,
                    "exercise_level": exercise.level,
                    "talk_phase": "prompt",
                    "retry_available": False,
                    "new_phrase_available": False,
                    "profile": profile_to_metadata(profile),
                    "evaluation_score": 0.0,
                    "evaluation_errors": [],
                    "next_focus": "Listen to the phrase and pronounce it clearly.",
                },
            )

        if lowered in {"retry", "again", "reintentar", "otra vez"}:
            exercise = self._manager.restart(user_id, level=profile.difficulty_level)
            return OrchestrationResult(
                selected_mode="free",
                final_text=f"Try again with this phrase:\n\n{exercise.phrase}",
                steps=[AgentStep("supervisor", "Orion", "free", "completed", "Supervisor asked for another attempt on the same phrase.", exercise.phrase)],
                metadata={
                    "selected_agent": "conversation",
                    "target_phrase": exercise.phrase,
                    "exercise_level": exercise.level,
                    "talk_phase": "prompt",
                    "retry_available": False,
                    "new_phrase_available": False,
                    "profile": profile_to_metadata(profile),
                    "evaluation_score": 0.0,
                    "evaluation_errors": [],
                    "next_focus": "Focus on the same phrase and pronounce it more clearly.",
                },
            )

        evaluation = self._manager.evaluate(user_id, content)
        final_text = (
            f"Target phrase: {evaluation['target_phrase']}\n"
            f"Your pronunciation transcript: {evaluation['transcript']}\n\n"
            f"Score: {int(float(evaluation['score']) * 100)}%\n"
            f"{evaluation['feedback']}\n\n"
            "Do you want to retry or get a new phrase?"
        )
        metadata = {
            "selected_agent": "conversation",
            "target_phrase": evaluation["target_phrase"],
            "transcript": evaluation["transcript"],
            "exercise_level": evaluation["level"],
            "talk_phase": "feedback",
            "retry_available": True,
            "new_phrase_available": True,
        }
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(
            user_id=user_id,
            source=source,
            original_input=content,
            selected_mode="free",
            final_text=final_text,
            metadata=metadata,
        )
        metadata["evaluation_score"] = evaluation["score"]
        metadata["evaluation_errors"] = [] if float(evaluation["score"]) >= 0.72 else ["pronunciation-needs-practice"]
        metadata["next_focus"] = learning_note
        metadata["profile"] = profile_to_metadata(updated_profile)
        metadata["strengths"] = evaluation_report.strengths
        return OrchestrationResult(
            selected_mode="free",
            final_text=final_text,
            steps=[AgentStep("supervisor", "Orion", "free", "completed", "Supervisor evaluated the pronunciation attempt.", final_text)],
            metadata=metadata,
        )


def _normalize_phrase(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def _normalize_level(level: str) -> str:
    return level if level in {"A2", "B1", "B2", "C1"} else "B1"
