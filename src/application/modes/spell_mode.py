from __future__ import annotations

from dataclasses import dataclass
import re

from src.application.modes.grammar_mode import profile_to_metadata
from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


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

    def start_from_choice(self, user_id: str, content: str, level: str = "B1", used_words: list[str] | None = None) -> SpellSession:
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
            return {"is_correct": False, "feedback": "There is no active spelling word yet.", "target_word": "", "recognized_word": ""}
        recognized = "".join(re.findall(r"[a-z]", spelled_text.lower()))
        target = session.current_word.lower()
        is_correct = recognized == target
        feedback = f"Correct. You spelled '{target}' well." if is_correct else f"Not yet. I heard '{recognized or 'nothing clear'}', but the target word is '{target}'."
        session.awaiting_retry_decision = True
        return {"is_correct": is_correct, "feedback": feedback, "target_word": target, "recognized_word": recognized, "has_next_word": session.index < len(session.words) - 1}

    def handle_followup(self, user_id: str, decision: str, used_words: list[str] | None = None) -> dict[str, object]:
        session = self.current(user_id)
        if session is None:
            return {"status": "missing", "message": "There is no active spelling session."}
        lowered = decision.lower()
        if any(token in lowered for token in ("retry", "again", "otra vez", "reintentar")):
            session.awaiting_retry_decision = False
            return {"status": "retry", "message": f"Try spelling '{session.current_word}' again.", "target_word": session.current_word}
        if session.index < len(session.words) - 1:
            session.index += 1
            session.awaiting_retry_decision = False
            return {"status": "next", "message": f"Great. Now spell '{session.current_word}'.", "target_word": session.current_word}
        self._active_sessions.pop(user_id, None)
        next_word = self._next_proposed_word(session.level, used_words or [])
        self._active_sessions[user_id] = SpellSession(words=[next_word], index=0, level=session.level)
        return {"status": "fresh", "message": f"That list is finished. A new suggested word is '{next_word}'. Spell it if you want to continue.", "target_word": next_word}

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


class SpellModeWorkflow:
    def __init__(self, manager: SpellPracticeManager, memory, router, agents: dict[str, object]) -> None:
        self._manager = manager
        self._memory = memory
        self._router = router
        self._agents = agents

    def handle(self, content: str, user_id: str, profile: UserProfile, source: str) -> OrchestrationResult:
        session = self._manager.current(user_id)
        used_words = [str(item.get("word", "")).strip().lower() for item in self._memory.system_snapshot(user_id).get("spelling_history", []) if str(item.get("word", "")).strip()]
        if session is None:
            lowered = content.lower().strip()
            if lowered in {"spell", "spelling", "begin", "help", "hola", "hello", "intro"}:
                return OrchestrationResult(
                    selected_mode="spelling",
                    final_text="I am Glyph.\n\nYou can give me a list of words separated by commas.\n\nOr write: start\n\nIf you write start, I will suggest one word for you.",
                    steps=[AgentStep("supervisor", "Orion", "spelling", "completed", "Supervisor introduced the spelling activity.", "Waiting for a list or a request to propose words.")],
                    metadata={"selected_agent": "spelling", "spelling_phase": "choice", "evaluation_score": 0.0, "evaluation_errors": [], "next_focus": "Write a word list, or write start to get a suggested word.", "profile": profile_to_metadata(profile)},
                )
            content_for_choice = "propose" if lowered in {"start", "iniciar"} else content
            session = self._manager.start_from_choice(user_id, content_for_choice, level=profile.difficulty_level, used_words=used_words)
            return OrchestrationResult(
                selected_mode="spelling",
                final_text=f"Spell this word: {session.current_word}",
                steps=[AgentStep("supervisor", "Orion", "spelling", "completed", "Supervisor selected the current spelling word.", session.current_word)],
                metadata={"selected_agent": "spelling", "target_word": session.current_word, "exercise_level": session.level, "spelling_phase": "word", "evaluation_score": 0.0, "evaluation_errors": [], "next_focus": "Spell the target word letter by letter.", "profile": profile_to_metadata(profile)},
            )
        if session.awaiting_retry_decision:
            followup = self._manager.handle_followup(user_id, content, used_words=used_words)
            return OrchestrationResult(
                selected_mode="spelling",
                final_text=followup["message"],
                steps=[AgentStep("supervisor", "Orion", "spelling", "completed", "Supervisor handled the next-step decision for spelling.", followup["message"])],
                metadata={"selected_agent": "spelling", "target_word": followup.get("target_word", ""), "exercise_level": session.level, "spelling_phase": "word", "evaluation_score": 0.0, "evaluation_errors": [], "next_focus": "Spell the shown word carefully.", "profile": profile_to_metadata(profile)},
            )

        primary_result, primary_step = self._agents["spelling"].run(self._router, content, context={"difficulty_level": profile.difficulty_level})
        evaluation = self._manager.evaluate_spelling(user_id, content)
        final_text = f"{evaluation['feedback']}\n\nDo you want to retry this word or move to the next one?"
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(user_id=user_id, source=source, original_input=content, selected_mode="spelling", final_text=final_text, metadata={"target_word": evaluation["target_word"]})
        return OrchestrationResult(
            selected_mode="spelling",
            final_text=final_text,
            steps=[primary_step],
            metadata={
                "selected_agent": "spelling",
                "feedback": primary_result.metadata.get("feedback", evaluation["feedback"]),
                "target_word": evaluation["target_word"],
                "recognized_word": evaluation["recognized_word"],
                "exercise_level": session.level,
                "spelling_phase": "feedback",
                "evaluation_score": 1.0 if evaluation["is_correct"] else 0.45,
                "evaluation_errors": [] if evaluation["is_correct"] else ["spelling-mismatch"],
                "next_focus": learning_note,
                "profile": profile_to_metadata(updated_profile),
                "strengths": evaluation_report.strengths,
            },
        )


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
