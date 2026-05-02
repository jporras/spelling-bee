from __future__ import annotations

from src.domain.entities import EvaluationReport, UserProfile


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
