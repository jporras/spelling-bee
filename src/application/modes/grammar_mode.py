from __future__ import annotations

from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


class GrammarModeWorkflow:
    def __init__(self, router, memory, agents: dict[str, object]) -> None:
        self._router = router
        self._memory = memory
        self._agents = agents

    def handle(
        self,
        content: str,
        user_id: str,
        profile: UserProfile,
        source: str,
        selected_mode: str = "grammar",
    ) -> OrchestrationResult:
        primary_agent = self._agents["grammar"] if selected_mode == "grammar" else self._agents["conversation"]
        planning_step = AgentStep(
            agent_id="supervisor",
            display_name="Orion",
            mode=selected_mode,
            state="completed",
            summary=f"Supervisor routed the request to {primary_agent.display_name}.",
            output="Routing complete.",
        )
        primary_result, primary_step = primary_agent.run(
            self._router,
            content,
            context={"difficulty_level": profile.difficulty_level},
        )
        steps = [planning_step, primary_step]
        final_text = primary_result.content
        metadata = dict(primary_result.metadata)
        metadata["routed_by"] = "Orion"
        metadata["selected_agent"] = primary_agent.agent_id
        metadata["difficulty_level"] = profile.difficulty_level

        if selected_mode == "grammar":
            original_voice_result, original_voice_step = self._agents["voice"].run(
                self._router,
                content,
                context={"difficulty_level": profile.difficulty_level},
            )
            original_voice_step.summary = "Reads the original sentence aloud."
            corrected_voice_result, corrected_voice_step = self._agents["voice"].run(
                self._router,
                primary_result.content,
                context={"difficulty_level": profile.difficulty_level},
            )
            corrected_voice_step.summary = "Reads the corrected sentence aloud."
            steps.extend([original_voice_step, corrected_voice_step])
            metadata["original_voice_preview"] = original_voice_result.content
            metadata["voice_preview"] = corrected_voice_result.content
            metadata["suggestion"] = _suggest_better_phrase(primary_result.content)
            final_text = f"Corrected sentence: {primary_result.content}\n\nSuggestion: {metadata['suggestion']}"
        else:
            voice_result, voice_step = self._agents["voice"].run(
                self._router,
                primary_result.content,
                context={"difficulty_level": profile.difficulty_level},
            )
            voice_step.summary = "Formats the corrected text for speech playback."
            steps.append(voice_step)
            metadata["voice_preview"] = voice_result.content

        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(
            user_id=user_id,
            source=source,
            original_input=content,
            selected_mode=selected_mode,
            final_text=final_text,
            metadata=metadata,
        )
        steps.extend(
            [
                AgentStep(
                    agent_id="evaluation",
                    display_name="Vera",
                    mode="meta",
                    state="completed",
                    summary="Evaluated interaction quality and detected error patterns.",
                    output=", ".join(evaluation_report.errors) or "No major errors detected.",
                ),
                AgentStep(
                    agent_id="learning",
                    display_name="Atlas",
                    mode="meta",
                    state="completed",
                    summary="Updated memory and next-step recommendation.",
                    output=learning_note,
                ),
            ]
        )
        metadata["evaluation_score"] = evaluation_report.score
        metadata["evaluation_errors"] = evaluation_report.errors
        metadata["strengths"] = evaluation_report.strengths
        metadata["next_focus"] = learning_note
        metadata["profile"] = profile_to_metadata(updated_profile)
        return OrchestrationResult(
            selected_mode=selected_mode,
            final_text=final_text,
            steps=steps,
            metadata=metadata,
        )


def profile_to_metadata(profile: UserProfile) -> dict[str, object]:
    return {
        "user_id": profile.user_id,
        "difficulty_level": profile.difficulty_level,
        "total_interactions": profile.total_interactions,
        "recent_errors": profile.recent_errors,
        "last_transcript": profile.last_transcript,
        "notes": profile.notes,
    }


def _suggest_better_phrase(text: str) -> str:
    lowered = text.lower().strip()
    if lowered.startswith("i want "):
        return text.replace("I want", "I would like", 1)
    if lowered.startswith("i am going to"):
        return text.replace("I am going to", "I'm going to", 1)
    if lowered.startswith("can you tell me"):
        return text.replace("Can you tell me", "Could you tell me", 1)
    return f"Another natural option is: {text}"
