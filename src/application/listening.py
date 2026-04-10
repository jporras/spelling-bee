from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ListeningExercise:
    exercise_id: str
    level: str
    passage: str
    question: str
    expected_keywords: tuple[str, ...]
    answer_hint: str


class ListeningExerciseManager:
    def __init__(self) -> None:
        self._active_sessions: dict[str, ListeningExercise] = {}
        self._seed_index_by_level = {"A2": 0, "B1": 0, "B2": 0, "C1": 0}
        self._exercises_by_level = {
            "A2": (
                ListeningExercise(
                    exercise_id="park",
                    level="A2",
                    passage="Tom went to the park after lunch. He played football with two friends.",
                    question="Where did Tom go after lunch?",
                    expected_keywords=("park",),
                    answer_hint="He went to the park.",
                ),
                ListeningExercise(
                    exercise_id="breakfast",
                    level="A2",
                    passage="Sara had eggs and toast for breakfast before school.",
                    question="What did Sara eat for breakfast?",
                    expected_keywords=("eggs", "toast"),
                    answer_hint="She ate eggs and toast.",
                ),
            ),
            "B1": (
                ListeningExercise(
                    exercise_id="library",
                    level="B1",
                    passage=(
                        "Emma went to the library after school because she needed a book for her history class. "
                        "She borrowed a book about ancient Egypt and planned to read it that evening."
                    ),
                    question="Why did Emma go to the library?",
                    expected_keywords=("history", "book", "class"),
                    answer_hint="She went because she needed a book for her history class.",
                ),
                ListeningExercise(
                    exercise_id="market",
                    level="B1",
                    passage=(
                        "On Saturday morning, Diego walked to the market with his sister. "
                        "They bought fresh fruit, bread, and some cheese for lunch."
                    ),
                    question="What did Diego and his sister buy?",
                    expected_keywords=("fruit", "bread", "cheese"),
                    answer_hint="They bought fruit, bread, and cheese.",
                ),
            ),
            "B2": (
                ListeningExercise(
                    exercise_id="train",
                    level="B2",
                    passage=(
                        "Lina missed the first train, so she took the next one and arrived ten minutes late to work. "
                        "She sent a message to her manager while she was waiting on the platform."
                    ),
                    question="Why did Lina arrive late to work?",
                    expected_keywords=("missed", "train", "next"),
                    answer_hint="She arrived late because she missed the first train and had to take the next one.",
                ),
                ListeningExercise(
                    exercise_id="presentation",
                    level="B2",
                    passage=(
                        "Marcus spent the evening practicing his presentation because he wanted to feel confident the next day. "
                        "He also printed extra notes in case his slides failed."
                    ),
                    question="Why did Marcus print extra notes?",
                    expected_keywords=("slides", "failed", "notes"),
                    answer_hint="He printed extra notes in case his slides failed.",
                ),
            ),
            "C1": (
                ListeningExercise(
                    exercise_id="proposal",
                    level="C1",
                    passage=(
                        "Although the committee appreciated the creativity of the proposal, they postponed the decision until they could review the budget in more detail. "
                        "For that reason, Elena revised the financial section before the next meeting."
                    ),
                    question="Why did Elena revise the financial section?",
                    expected_keywords=("budget", "detail", "meeting"),
                    answer_hint="She revised it because the committee wanted to review the budget in more detail before deciding.",
                ),
                ListeningExercise(
                    exercise_id="documentary",
                    level="C1",
                    passage=(
                        "After watching the documentary, the students discussed how media can shape public opinion, especially when complex issues are presented too simply. "
                        "Their teacher asked them to compare the film with a newspaper article on the same topic."
                    ),
                    question="What comparison did the teacher ask the students to make?",
                    expected_keywords=("film", "newspaper", "article"),
                    answer_hint="The teacher asked them to compare the documentary with a newspaper article on the same topic.",
                ),
            ),
        }

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
            return {
                "matched_keywords": [],
                "score": 0.0,
                "is_correct": False,
                "feedback": "There is no active listening question yet.",
                "expected_answer": "",
            }

        lowered = response.lower()
        matched = [keyword for keyword in exercise.expected_keywords if keyword in lowered]
        score = len(matched) / len(exercise.expected_keywords)
        is_correct = score >= 0.5
        if is_correct:
            feedback = (
                "Good answer. You captured the main idea of the paragraph."
                if score < 1.0
                else "Excellent. Your answer matched the key information from the paragraph."
            )
        else:
            feedback = (
                "Not quite yet. Try to focus on the key detail that answers the question."
            )
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


def _normalize_level(level: str) -> str:
    return level if level in {"A2", "B1", "B2", "C1"} else "B1"
