from __future__ import annotations

from dataclasses import dataclass

from src.application.agents import build_default_agents
from src.application.modes import GrammarModeWorkflow, ListenModeWorkflow, ListeningExerciseManager, SpellModeWorkflow, SpellPracticeManager, TalkModeWorkflow, TalkPracticeManager
from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


@dataclass(slots=True)
class RouteDecision:
    mode: str
    reason: str


class SupervisorAgent:
    def __init__(self, router, memory) -> None:
        self._router = router
        self._memory = memory
        self._sub_agents = build_default_agents()
        self._listen_workflow = ListenModeWorkflow(ListeningExerciseManager(), memory)
        self._talk_workflow = TalkModeWorkflow(TalkPracticeManager(), memory)
        self._spell_workflow = SpellModeWorkflow(SpellPracticeManager(), memory, router, self._sub_agents)
        self._grammar_workflow = GrammarModeWorkflow(router, memory, self._sub_agents)

    def available_agents(self) -> list:
        return list(self._sub_agents.values())

    def handle(self, content: str, preferred_mode: str | None = None, user_id: str = "guest") -> OrchestrationResult:
        return self._handle_text(content=content, preferred_mode=preferred_mode, user_id=user_id)

    def handle_audio(self, audio_path: str, preferred_mode: str | None = None, user_id: str = "guest") -> OrchestrationResult:
        profile = self._memory.load_profile(user_id)
        transcription_result, transcription_step = self._sub_agents["transcription"].run(self._router, audio_path, context={"difficulty_level": profile.difficulty_level})
        orchestration = self._handle_text(content=transcription_result.content, preferred_mode=preferred_mode, user_id=user_id, source="audio")
        orchestration.steps.insert(1, transcription_step)
        orchestration.metadata["transcript"] = transcription_result.content
        orchestration.metadata["audio_path"] = audio_path
        return orchestration

    def user_snapshot(self, user_id: str = "guest") -> dict[str, object]:
        return self._memory.system_snapshot(user_id)

    def persist_exit_summary(self, user_id: str = "guest") -> dict[str, object]:
        return self._memory.persist_exit_summary(user_id)

    def speak_text(self, content: str, user_id: str = "guest") -> str:
        profile = self._memory.load_profile(user_id)
        voice_result, _ = self._sub_agents["voice"].run(self._router, content, context={"difficulty_level": profile.difficulty_level})
        return voice_result.content

    def _handle_text(self, content: str, preferred_mode: str | None = None, user_id: str = "guest", source: str = "text") -> OrchestrationResult:
        profile = self._memory.load_profile(user_id)
        if preferred_mode == "listen":
            return self._listen_workflow.handle(content, user_id, profile, source)
        if preferred_mode == "free":
            return self._talk_workflow.handle(content, user_id, profile, source)
        if preferred_mode == "spelling":
            return self._spell_workflow.handle(content, user_id, profile, source)
        if preferred_mode == "grammar":
            return self._grammar_workflow.handle(content, user_id, profile, source, selected_mode="grammar")

        decision = self._decide_route(content=content, preferred_mode=preferred_mode, profile=profile)
        if decision.mode == "listen":
            return self._listen_workflow.handle(content, user_id, profile, source)
        if decision.mode == "spelling":
            return self._handle_direct_spelling(content, user_id, profile, source, decision)
        if decision.mode == "tts":
            return self._handle_tts(content, profile)
        return self._grammar_workflow.handle(content, user_id, profile, source, selected_mode="free")

    def _handle_tts(self, content: str, profile: UserProfile) -> OrchestrationResult:
        planning_step = AgentStep("supervisor", "Orion", "tts", "completed", "Supervisor detected a speech playback request.", "Routing complete.")
        voice_result, voice_step = self._sub_agents["voice"].run(self._router, content, context={"difficulty_level": profile.difficulty_level})
        return OrchestrationResult(
            selected_mode="tts",
            final_text=voice_result.content,
            steps=[planning_step, voice_step],
            metadata={"routed_by": "Orion", "selected_agent": "voice", "difficulty_level": profile.difficulty_level, "voice_preview": voice_result.content, "evaluation_score": 0.0, "evaluation_errors": []},
        )

    def _handle_direct_spelling(
        self,
        content: str,
        user_id: str,
        profile: UserProfile,
        source: str,
        decision: RouteDecision,
    ) -> OrchestrationResult:
        planning_step = AgentStep("supervisor", "Orion", "spelling", "completed", decision.reason, "Routing complete.")
        primary_result, primary_step = self._sub_agents["spelling"].run(
            self._router,
            content,
            context={"difficulty_level": profile.difficulty_level},
        )
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(
            user_id=user_id,
            source=source,
            original_input=content,
            selected_mode="spelling",
            final_text=primary_result.content,
            metadata=primary_result.metadata,
        )
        metadata = dict(primary_result.metadata)
        metadata["routed_by"] = "Orion"
        metadata["selected_agent"] = "spelling"
        metadata["difficulty_level"] = updated_profile.difficulty_level
        metadata["evaluation_score"] = evaluation_report.score
        metadata["evaluation_errors"] = evaluation_report.errors
        metadata["strengths"] = evaluation_report.strengths
        metadata["next_focus"] = learning_note
        metadata["profile"] = {
            "user_id": updated_profile.user_id,
            "difficulty_level": updated_profile.difficulty_level,
            "total_interactions": updated_profile.total_interactions,
            "recent_errors": updated_profile.recent_errors,
            "last_transcript": updated_profile.last_transcript,
            "notes": updated_profile.notes,
        }
        return OrchestrationResult(
            selected_mode="spelling",
            final_text=primary_result.content,
            steps=[planning_step, primary_step],
            metadata=metadata,
        )

    def _decide_route(self, content: str, preferred_mode: str | None, profile: UserProfile) -> RouteDecision:
        if preferred_mode and preferred_mode != "auto":
            return RouteDecision(mode=preferred_mode, reason=f"Supervisor accepted manual mode '{preferred_mode}'.")
        lowered = content.lower()
        if any(token in lowered for token in ("grammar", "grammatical", "check grammar", "correct grammar")):
            return RouteDecision(mode="grammar", reason="Supervisor detected an explicit grammar evaluation request.")
        if any(token in lowered for token in ("listen", "listening", "question about", "answer the question")):
            return RouteDecision(mode="listen", reason="Supervisor detected a listening-comprehension request.")
        if any(token in lowered for token in ("spell", "spelling", "letters", "letter by letter")):
            return RouteDecision(mode="spelling", reason="Supervisor detected a spelling-oriented request.")
        if any(token in lowered for token in ("say", "speak", "voice", "read aloud", "pronounce")):
            return RouteDecision(mode="tts", reason="Supervisor detected a speech playback request.")
        return RouteDecision(mode="free", reason=f"Supervisor selected Nova for the correction-oriented tutoring flow. Current learner level: {profile.difficulty_level}.")
