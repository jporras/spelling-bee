from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone

from src.domain.entities import EvaluationReport, InteractionRecord, UserProfile
from src.infrastructure.persistence.user_store import UserStore


class DifficultyService:
    LEVELS = ("A2", "B1", "B2", "C1")

    def update_level(self, profile: UserProfile, report: EvaluationReport) -> str:
        score = report.score
        current_index = self.LEVELS.index(profile.difficulty_level)
        if score >= 0.9 and current_index < len(self.LEVELS) - 1:
            return self.LEVELS[current_index + 1]
        if score <= 0.45 and current_index > 0:
            return self.LEVELS[current_index - 1]
        return profile.difficulty_level


class EvaluationAgent:
    def evaluate(self, original_input: str, selected_mode: str, final_text: str) -> EvaluationReport:
        lowered = original_input.lower()
        errors: list[str] = []
        strengths: list[str] = []
        score = 0.82

        if selected_mode == "free":
            if " are " in f" {lowered} " and " is " in f" {final_text.lower()} ":
                errors.append("subject-verb-agreement")
                strengths.append("Accepted grammar correction.")
                score = 0.86
            if original_input and original_input[:1].islower():
                errors.append("capitalization")
                score -= 0.08
        elif selected_mode == "spelling":
            if " " in final_text.strip():
                strengths.append("Separated letters clearly.")
            else:
                errors.append("spelling-segmentation")
                score = 0.6
        elif selected_mode == "tts":
            strengths.append("Requested pronunciation or speaking support.")
            score = 0.88

        if not strengths:
            strengths.append("Completed an interaction successfully.")

        next_focus = "Practice the same pattern with a harder sentence."
        if errors:
            next_focus = f"Focus on {errors[0].replace('-', ' ')} in the next turn."

        return EvaluationReport(
            score=max(0.1, min(score, 0.99)),
            errors=errors,
            strengths=strengths,
            next_focus=next_focus,
        )


class LearningAgent:
    def suggest(self, profile: UserProfile, report: EvaluationReport) -> str:
        if report.errors:
            return f"Next micro-goal: reinforce {report.errors[0].replace('-', ' ')}."
        if profile.difficulty_level in {"A2", "B1"}:
            return "Next micro-goal: expand sentence variety with everyday topics."
        return "Next micro-goal: add nuance, connectors, and longer responses."


class MemoryManager:
    def __init__(self, store: UserStore) -> None:
        self._store = store
        self._difficulty_service = DifficultyService()
        self._evaluation_agent = EvaluationAgent()
        self._learning_agent = LearningAgent()

    def load_profile(self, user_id: str) -> UserProfile:
        return self._store.load_profile(user_id)

    def list_recent_interactions(self, user_id: str, limit: int = 5) -> list[InteractionRecord]:
        return self._store.load_interactions(user_id)[-limit:]

    def register_interaction(
        self,
        user_id: str,
        source: str,
        original_input: str,
        selected_mode: str,
        final_text: str,
        metadata: dict[str, object] | None = None,
    ) -> tuple[UserProfile, EvaluationReport, str]:
        profile = self._store.load_profile(user_id)
        report = self._evaluation_agent.evaluate(
            original_input=original_input,
            selected_mode=selected_mode,
            final_text=final_text,
        )

        profile.total_interactions += 1
        profile.preferred_modes[selected_mode] = profile.preferred_modes.get(selected_mode, 0) + 1
        if selected_mode == "free":
            profile.correction_count += 1
        elif selected_mode == "spelling":
            profile.spelling_count += 1
        elif selected_mode in {"tts", "transcription"}:
            profile.pronunciation_count += 1

        profile.recent_errors = _merge_recent_errors(profile.recent_errors, report.errors)
        profile.difficulty_level = self._difficulty_service.update_level(profile, report)
        learning_note = self._learning_agent.suggest(profile, report)
        profile.notes = (profile.notes + [learning_note])[-5:]
        profile.last_transcript = original_input

        record = InteractionRecord(
            user_id=user_id,
            source=source,
            original_input=original_input,
            selected_mode=selected_mode,
            final_text=final_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            difficulty_level=profile.difficulty_level,
            evaluation_score=report.score,
            errors=report.errors,
        )
        self._store.save_profile(profile)
        self._store.append_interaction(record)
        self._store.save_session_summary(
            user_id=user_id,
            selected_mode=selected_mode,
            level=profile.difficulty_level,
            evaluation_score=report.score,
            next_focus=learning_note,
            summary=final_text[:280],
        )
        target_word = str((metadata or {}).get("target_word", "")).strip().lower()
        if selected_mode == "spelling" and target_word:
            was_correct = "spelling-mismatch" not in report.errors
            self._store.record_spelling_word(user_id, target_word, was_correct)
        return profile, report, learning_note

    def system_snapshot(self, user_id: str) -> dict[str, object]:
        profile = self._store.load_profile(user_id)
        interactions = self._store.load_interactions(user_id)
        mode_counter = Counter(record.selected_mode for record in interactions)
        recent_scores = [record.evaluation_score for record in interactions[-10:]]
        level_progress = {
            level: index for index, level in enumerate(self._difficulty_service.LEVELS, start=1)
        }
        average_score = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else 0.0
        mode_usage = {
            "grammar": mode_counter.get("grammar", 0),
            "talk": mode_counter.get("free", 0),
            "listen": mode_counter.get("listen", 0),
            "spell": mode_counter.get("spelling", 0),
        }
        last_session = self._store.load_last_session(user_id)
        spelling_history = self._store.load_spelling_history(user_id, limit=8)
        return {
            "profile": asdict(profile),
            "top_mode": mode_counter.most_common(1)[0][0] if mode_counter else "free",
            "interaction_count": len(interactions),
            "average_score": average_score,
            "recent_scores": recent_scores,
            "mode_usage": mode_usage,
            "level_index": level_progress.get(profile.difficulty_level, 2),
            "level_scale": len(self._difficulty_service.LEVELS),
            "last_session": last_session,
            "spelling_history": spelling_history,
        }

    def persist_exit_summary(self, user_id: str) -> dict[str, object]:
        snapshot = self.system_snapshot(user_id)
        profile = snapshot["profile"]
        average_score = float(snapshot.get("average_score", 0.0))
        top_mode = str(snapshot.get("top_mode", "free"))
        notes = profile.get("notes", [])
        next_focus = notes[-1] if notes else "Continue with the next recommended activity."
        interaction_count = int(snapshot.get("interaction_count", 0))
        recent_words = [item["word"] for item in snapshot.get("spelling_history", [])[:3]]
        spell_memory = f" Recent spell words: {', '.join(recent_words)}." if recent_words else ""
        summary = (
            f"Session checkpoint for {profile.get('user_id', user_id)}. "
            f"Level: {profile.get('difficulty_level', 'B1')}. "
            f"Interactions: {interaction_count}. "
            f"Average score: {int(average_score * 100)}%. "
            f"Top mode: {top_mode}.{spell_memory}"
        )
        self._store.save_session_summary(
            user_id=user_id,
            selected_mode=top_mode,
            level=str(profile.get("difficulty_level", "B1")),
            evaluation_score=average_score,
            next_focus=next_focus,
            summary=summary[:280],
        )
        snapshot["last_session"] = self._store.load_last_session(user_id)
        return snapshot


def _merge_recent_errors(existing: list[str], incoming: list[str]) -> list[str]:
    merged = existing + incoming
    return merged[-6:]
