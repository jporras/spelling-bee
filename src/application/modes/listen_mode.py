from __future__ import annotations

from dataclasses import dataclass

from src.application.modes.grammar_mode import profile_to_metadata
from src.application.modes.practice_content import PracticeContent, load_practice_content
from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


@dataclass(slots=True)
class ListeningExercise:
    exercise_id: str
    level: str
    passage: str
    question: str
    expected_keywords: tuple[str, ...]
    answer_hint: str


class ListeningExerciseManager:
    def __init__(self, practice_content: PracticeContent | None = None) -> None:
        practice_content = practice_content or load_practice_content()
        self._active_sessions: dict[str, ListeningExercise] = {}
        self._seed_index_by_level = {"A2": 0, "B1": 0, "B2": 0, "C1": 0}
        self._exercises_by_level = _build_exercises_by_level(practice_content)

    def has_active_session(self, user_id: str) -> bool:
        return user_id in self._active_sessions

    def start(self, user_id: str, level: str = "B1") -> ListeningExercise:
        normalized_level = _normalize_level(level)
        exercises = self._exercises_by_level[normalized_level]
        index = self._seed_index_by_level[normalized_level] % len(exercises)
        exercise = exercises[index]
        self._seed_index_by_level[normalized_level] += 1
        self._active_sessions[user_id] = exercise
        return exercise

    def current(self, user_id: str) -> ListeningExercise | None:
        return self._active_sessions.get(user_id)

    def evaluate(self, user_id: str, response: str) -> dict[str, object]:
        exercise = self._active_sessions.pop(user_id, None)
        if exercise is None:
            return {"matched_keywords": [], "score": 0.0, "is_correct": False, "feedback": "There is no active listening question yet.", "expected_answer": ""}
        lowered = response.lower()
        matched = [keyword for keyword in exercise.expected_keywords if keyword in lowered]
        score = len(matched) / len(exercise.expected_keywords)
        is_correct = score >= 0.5
        feedback = "Excellent. Your answer matched the key information from the paragraph." if score == 1.0 else "Good answer. You captured the main idea of the paragraph." if is_correct else "Not quite yet. Try to focus on the key detail that answers the question."
        return {
            "matched_keywords": matched,
            "score": score,
            "is_correct": is_correct,
            "feedback": feedback,
            "expected_answer": exercise.answer_hint,
            "question": exercise.question,
            "passage": exercise.passage,
            "level": exercise.level,
        }


class ListenModeWorkflow:
    def __init__(self, manager: ListeningExerciseManager, memory) -> None:
        self._manager = manager
        self._memory = memory

    def handle(self, content: str, user_id: str, profile: UserProfile, source: str) -> OrchestrationResult:
        if not self._manager.has_active_session(user_id):
            if content.lower().strip() not in {"start", "iniciar", "begin", "empezar"}:
                return OrchestrationResult(
                    selected_mode="listen",
                    final_text="I am Pulse.\n\nIn Listen mode I will share a short paragraph, read it aloud, and ask one question.\n\nTo begin, write: start",
                    steps=[AgentStep("supervisor", "Orion", "listen", "completed", "Supervisor introduced the listening activity.", "Waiting for the learner to type start.")],
                    metadata={"routed_by": "Orion", "selected_agent": "transcription", "difficulty_level": profile.difficulty_level, "listening_phase": "intro", "expecting_response": False, "profile": profile_to_metadata(profile), "evaluation_score": 0.0, "evaluation_errors": [], "next_focus": "Write start when you want the listening exercise."},
                )
            exercise = self._manager.start(user_id, level=profile.difficulty_level)
            return OrchestrationResult(
                selected_mode="listen",
                final_text=f"{exercise.passage}\n\nQuestion: {exercise.question}",
                steps=[AgentStep("supervisor", "Orion", "listen", "completed", "Supervisor started a listening-comprehension exercise.", "Listening prompt ready.")],
                metadata={"routed_by": "Orion", "selected_agent": "transcription", "difficulty_level": profile.difficulty_level, "speak_after_display": f"{exercise.passage} Question: {exercise.question}", "listening_phase": "question", "listening_question": exercise.question, "listening_passage": exercise.passage, "exercise_level": exercise.level, "expecting_response": True, "profile": profile_to_metadata(profile), "evaluation_score": 0.0, "evaluation_errors": [], "next_focus": "Listen carefully and answer the question in your own words."},
            )

        evaluation = self._manager.evaluate(user_id, content)
        final_text = f"{evaluation['feedback']}\n\nSuggested answer: {evaluation['expected_answer']}" if not evaluation["is_correct"] else f"{evaluation['feedback']}\n\nExpected idea: {evaluation['expected_answer']}"
        final_text = f"{final_text}\n\nTo try another listening exercise, write: start\nIf you want to practice a different skill, choose another mode above."
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(user_id=user_id, source=source, original_input=content, selected_mode="listen", final_text=final_text, metadata={"question": evaluation["question"]})
        return OrchestrationResult(
            selected_mode="listen",
            final_text=final_text,
            steps=[
                AgentStep("supervisor", "Orion", "listen", "completed", "Supervisor evaluated the listening answer.", final_text),
                AgentStep("evaluation", "Vera", "meta", "completed", "Checked whether the answer captured the main idea.", ", ".join(evaluation["matched_keywords"]) or "No key ideas matched."),
                AgentStep("learning", "Atlas", "meta", "completed", "Stored the result and updated the next practice step.", learning_note),
            ],
            metadata={"routed_by": "Orion", "selected_agent": "transcription", "difficulty_level": updated_profile.difficulty_level, "listening_phase": "feedback", "listening_question": evaluation["question"], "listening_passage": evaluation["passage"], "exercise_level": evaluation["level"], "matched_keywords": evaluation["matched_keywords"], "expecting_response": False, "evaluation_score": evaluation["score"], "evaluation_errors": [] if evaluation["is_correct"] else ["Listening answer missed key details."], "next_focus": learning_note, "profile": profile_to_metadata(updated_profile), "strengths": evaluation_report.strengths},
        )


def _normalize_level(level: str) -> str:
    return level if level in {"A2", "B1", "B2", "C1"} else "B1"


def _build_exercises_by_level(
    practice_content: PracticeContent,
) -> dict[str, tuple[ListeningExercise, ...]]:
    exercises_by_level: dict[str, tuple[ListeningExercise, ...]] = {}
    for level, exercises in practice_content.listening_exercises.items():
        exercises_by_level[level] = tuple(
            ListeningExercise(
                exercise_id=str(exercise["id"]),
                level=level,
                passage=str(exercise["passage"]),
                question=str(exercise["question"]),
                expected_keywords=tuple(str(keyword) for keyword in exercise["expected_keywords"]),
                answer_hint=str(exercise["answer_hint"]),
            )
            for exercise in exercises
        )
    return exercises_by_level
