from __future__ import annotations

from dataclasses import dataclass

from src.application.agent import Agent
from src.application.listening import ListeningExerciseManager
from src.application.memory import MemoryManager
from src.application.practice_modes import SpellPracticeManager, TalkPracticeManager
from src.application.sub_agents import SubAgent
from src.domain.entities import AgentStep, OrchestrationResult, UserProfile


@dataclass(slots=True)
class RouteDecision:
    mode: str
    reason: str


class SupervisorAgent:
    def __init__(self, router: Agent, memory: MemoryManager) -> None:
        self._router = router
        self._memory = memory
        self._listening = ListeningExerciseManager()
        self._talk = TalkPracticeManager()
        self._spell = SpellPracticeManager()
        self._sub_agents: dict[str, SubAgent] = {
            "transcription": SubAgent(
                agent_id="transcription",
                display_name="Pulse",
                mode="transcription",
                role="Turns microphone audio into text.",
            ),
            "learning": SubAgent(
                agent_id="learning",
                display_name="Atlas",
                mode="free",
                role="Tracks progress and proposes the next learning focus.",
                routable=False,
            ),
            "evaluation": SubAgent(
                agent_id="evaluation",
                display_name="Vera",
                mode="free",
                role="Evaluates the quality of each learning interaction.",
                routable=False,
            ),
            "conversation": SubAgent(
                agent_id="conversation",
                display_name="Nova",
                mode="free",
                role="Improves grammar and explains corrections.",
            ),
            "grammar": SubAgent(
                agent_id="grammar",
                display_name="Nova",
                mode="grammar",
                role="Evaluates grammar and explains the mistakes clearly.",
            ),
            "spelling": SubAgent(
                agent_id="spelling",
                display_name="Glyph",
                mode="spelling",
                role="Validates spelling letter by letter.",
            ),
            "voice": SubAgent(
                agent_id="voice",
                display_name="Echo",
                mode="tts",
                role="Prepares the response for spoken playback.",
            ),
        }

    def available_agents(self) -> list[SubAgent]:
        return list(self._sub_agents.values())

    def handle(
        self,
        content: str,
        preferred_mode: str | None = None,
        user_id: str = "guest",
    ) -> OrchestrationResult:
        return self._handle_text(content=content, preferred_mode=preferred_mode, user_id=user_id)

    def handle_audio(
        self,
        audio_path: str,
        preferred_mode: str | None = None,
        user_id: str = "guest",
    ) -> OrchestrationResult:
        profile = self._memory.load_profile(user_id)
        transcription_result, transcription_step = self._sub_agents["transcription"].run(
            self._router,
            audio_path,
            context={"difficulty_level": profile.difficulty_level},
        )
        orchestration = self._handle_text(
            content=transcription_result.content,
            preferred_mode=preferred_mode,
            user_id=user_id,
            source="audio",
        )
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
        voice_result, _ = self._sub_agents["voice"].run(
            self._router,
            content,
            context={"difficulty_level": profile.difficulty_level},
        )
        return voice_result.content

    def _handle_text(
        self,
        content: str,
        preferred_mode: str | None = None,
        user_id: str = "guest",
        source: str = "text",
    ) -> OrchestrationResult:
        profile = self._memory.load_profile(user_id)
        if preferred_mode == "listen":
            return self._handle_listen(content=content, user_id=user_id, profile=profile, source=source)
        if preferred_mode == "free":
            return self._handle_talk(content=content, user_id=user_id, profile=profile, source=source)
        if preferred_mode == "spelling":
            return self._handle_spell(content=content, user_id=user_id, profile=profile, source=source)
        decision = self._decide_route(content=content, preferred_mode=preferred_mode, profile=profile)
        primary_agent = self._agent_for_mode(decision.mode)

        planning_step = AgentStep(
            agent_id="supervisor",
            display_name="Orion",
            mode=decision.mode,
            state="completed",
            summary=decision.reason,
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

        if decision.mode == "grammar":
            original_voice_result, original_voice_step = self._sub_agents["voice"].run(
                self._router,
                content,
                context={"difficulty_level": profile.difficulty_level},
            )
            original_voice_step.summary = "Reads the original sentence aloud."
            corrected_voice_result, corrected_voice_step = self._sub_agents["voice"].run(
                self._router,
                primary_result.content,
                context={"difficulty_level": profile.difficulty_level},
            )
            corrected_voice_step.summary = "Reads the corrected sentence aloud."
            steps.extend([original_voice_step, corrected_voice_step])
            metadata["original_voice_preview"] = original_voice_result.content
            metadata["voice_preview"] = corrected_voice_result.content
            metadata["suggestion"] = _suggest_better_phrase(primary_result.content)
            final_text = (
                f"Corrected sentence: {primary_result.content}\n\n"
                f"Suggestion: {metadata['suggestion']}"
            )
        elif decision.mode in {"free"}:
            voice_result, voice_step = self._sub_agents["voice"].run(
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
            selected_mode=decision.mode,
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
        metadata["profile"] = _profile_to_metadata(updated_profile)

        return OrchestrationResult(
            selected_mode=decision.mode,
            final_text=final_text,
            steps=steps,
            metadata=metadata,
        )

    def _handle_listen(
        self,
        content: str,
        user_id: str,
        profile: UserProfile,
        source: str,
    ) -> OrchestrationResult:
        if not self._listening.has_active_session(user_id):
            if content.lower().strip() not in {"start", "iniciar", "begin", "empezar"}:
                return OrchestrationResult(
                    selected_mode="listen",
                    final_text=(
                        "I am Pulse.\n\n"
                        "In Listen mode I will share a short paragraph, read it aloud, and ask one question.\n\n"
                        "To begin, write: start"
                    ),
                    steps=[
                        AgentStep(
                            agent_id="supervisor",
                            display_name="Orion",
                            mode="listen",
                            state="completed",
                            summary="Supervisor introduced the listening activity.",
                            output="Waiting for the learner to type start.",
                        )
                    ],
                    metadata={
                        "routed_by": "Orion",
                        "selected_agent": "transcription",
                        "difficulty_level": profile.difficulty_level,
                        "listening_phase": "intro",
                        "expecting_response": False,
                        "profile": _profile_to_metadata(profile),
                        "evaluation_score": 0.0,
                        "evaluation_errors": [],
                        "next_focus": "Write start when you want the listening exercise.",
                    },
                )
            exercise = self._listening.start(user_id, level=profile.difficulty_level)
            planning_step = AgentStep(
                agent_id="supervisor",
                display_name="Orion",
                mode="listen",
                state="completed",
                summary="Supervisor started a listening-comprehension exercise.",
                output="Listening prompt ready.",
            )
            spoken_prompt = f"{exercise.passage} Question: {exercise.question}"
            metadata = {
                "routed_by": "Orion",
                "selected_agent": "transcription",
                "difficulty_level": profile.difficulty_level,
                "speak_after_display": spoken_prompt,
                "listening_phase": "question",
                "listening_question": exercise.question,
                "listening_passage": exercise.passage,
                "exercise_level": exercise.level,
                "expecting_response": True,
                "profile": _profile_to_metadata(profile),
                "evaluation_score": 0.0,
                "evaluation_errors": [],
                "next_focus": "Listen carefully and answer the question in your own words.",
            }
            return OrchestrationResult(
                selected_mode="listen",
                final_text=f"{exercise.passage}\n\nQuestion: {exercise.question}",
                steps=[planning_step],
                metadata=metadata,
            )

        evaluation = self._listening.evaluate(user_id, content)
        final_text = (
            f"{evaluation['feedback']}\n\nSuggested answer: {evaluation['expected_answer']}"
            if not evaluation["is_correct"]
            else f"{evaluation['feedback']}\n\nExpected idea: {evaluation['expected_answer']}"
        )
        final_text = (
            f"{final_text}\n\n"
            "To try another listening exercise, write: start\n"
            "If you want to practice a different skill, choose another mode above."
        )
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(
            user_id=user_id,
            source=source,
            original_input=content,
            selected_mode="listen",
            final_text=final_text,
            metadata={"question": evaluation["question"]},
        )
        steps = [
            AgentStep(
                agent_id="supervisor",
                display_name="Orion",
                mode="listen",
                state="completed",
                summary="Supervisor evaluated the listening answer.",
                output=final_text,
            ),
            AgentStep(
                agent_id="evaluation",
                display_name="Vera",
                mode="meta",
                state="completed",
                summary="Checked whether the answer captured the main idea.",
                output=", ".join(evaluation["matched_keywords"]) or "No key ideas matched.",
            ),
            AgentStep(
                agent_id="learning",
                display_name="Atlas",
                mode="meta",
                state="completed",
                summary="Stored the result and updated the next practice step.",
                output=learning_note,
            ),
        ]
        metadata = {
            "routed_by": "Orion",
            "selected_agent": "transcription",
            "difficulty_level": updated_profile.difficulty_level,
            "listening_phase": "feedback",
            "listening_question": evaluation["question"],
            "listening_passage": evaluation["passage"],
            "exercise_level": evaluation["level"],
            "matched_keywords": evaluation["matched_keywords"],
            "expecting_response": False,
            "evaluation_score": evaluation["score"],
            "evaluation_errors": [] if evaluation["is_correct"] else ["Listening answer missed key details."],
            "next_focus": learning_note,
            "profile": _profile_to_metadata(updated_profile),
            "strengths": evaluation_report.strengths,
        }
        return OrchestrationResult(
            selected_mode="listen",
            final_text=final_text,
            steps=steps,
            metadata=metadata,
        )

    def _handle_talk(
        self,
        content: str,
        user_id: str,
        profile: UserProfile,
        source: str,
    ) -> OrchestrationResult:
        current = self._talk.current(user_id)
        lowered = content.lower().strip()
        if current is None or lowered in {"new", "new phrase", "nueva", "nueva frase"}:
            exercise = self._talk.start(user_id, level=profile.difficulty_level)
            metadata = {
                "selected_agent": "conversation",
                "speak_after_display": exercise.phrase,
                "target_phrase": exercise.phrase,
                "exercise_level": exercise.level,
                "talk_phase": "prompt",
                "retry_available": False,
                "new_phrase_available": False,
                "profile": _profile_to_metadata(profile),
                "evaluation_score": 0.0,
                "evaluation_errors": [],
                "next_focus": "Listen to the phrase and pronounce it clearly.",
            }
            return OrchestrationResult(
                selected_mode="free",
                final_text=f"Repeat this phrase:\n\n{exercise.phrase}",
                steps=[
                    AgentStep(
                        agent_id="supervisor",
                        display_name="Orion",
                        mode="free",
                        state="completed",
                        summary="Supervisor started a pronunciation phrase.",
                        output=exercise.phrase,
                    )
                ],
                metadata=metadata,
            )

        if lowered in {"retry", "again", "reintentar", "otra vez"}:
            exercise = self._talk.restart(user_id, level=profile.difficulty_level)
            return OrchestrationResult(
                selected_mode="free",
                final_text=f"Try again with this phrase:\n\n{exercise.phrase}",
                steps=[
                    AgentStep(
                        agent_id="supervisor",
                        display_name="Orion",
                        mode="free",
                        state="completed",
                        summary="Supervisor asked for another attempt on the same phrase.",
                        output=exercise.phrase,
                    )
                ],
                metadata={
                    "selected_agent": "conversation",
                    "target_phrase": exercise.phrase,
                    "exercise_level": exercise.level,
                    "talk_phase": "prompt",
                    "retry_available": False,
                    "new_phrase_available": False,
                    "profile": _profile_to_metadata(profile),
                    "evaluation_score": 0.0,
                    "evaluation_errors": [],
                    "next_focus": "Focus on the same phrase and pronounce it more clearly.",
                },
            )

        evaluation = self._talk.evaluate(user_id, content)
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
        metadata["profile"] = _profile_to_metadata(updated_profile)
        metadata["strengths"] = evaluation_report.strengths
        return OrchestrationResult(
            selected_mode="free",
            final_text=final_text,
            steps=[
                AgentStep(
                    agent_id="supervisor",
                    display_name="Orion",
                    mode="free",
                    state="completed",
                    summary="Supervisor evaluated the pronunciation attempt.",
                    output=final_text,
                )
            ],
            metadata=metadata,
        )

    def _handle_spell(
        self,
        content: str,
        user_id: str,
        profile: UserProfile,
        source: str,
    ) -> OrchestrationResult:
        session = self._spell.current(user_id)
        used_words = [
            str(item.get("word", "")).strip().lower()
            for item in self._memory.system_snapshot(user_id).get("spelling_history", [])
            if str(item.get("word", "")).strip()
        ]
        if session is None:
            lowered = content.lower().strip()
            if lowered in {"spell", "spelling", "begin", "help", "hola", "hello", "intro"}:
                return OrchestrationResult(
                    selected_mode="spelling",
                    final_text=(
                        "I am Glyph.\n\n"
                        "You can give me a list of words separated by commas.\n\n"
                        "Or write: start\n\n"
                        "If you write start, I will suggest one word for you."
                    ),
                    steps=[
                        AgentStep(
                            agent_id="supervisor",
                            display_name="Orion",
                            mode="spelling",
                            state="completed",
                            summary="Supervisor introduced the spelling activity.",
                            output="Waiting for a list or a request to propose words.",
                        )
                    ],
                    metadata={
                        "selected_agent": "spelling",
                        "spelling_phase": "choice",
                        "evaluation_score": 0.0,
                        "evaluation_errors": [],
                        "next_focus": "Write a word list, or write start to get a suggested word.",
                        "profile": _profile_to_metadata(profile),
                    },
                )
            content_for_choice = "propose" if lowered in {"start", "iniciar"} else content
            session = self._spell.start_from_choice(
                user_id,
                content_for_choice,
                level=profile.difficulty_level,
                used_words=used_words,
            )
            return OrchestrationResult(
                selected_mode="spelling",
                final_text=f"Spell this word: {session.current_word}",
                steps=[
                    AgentStep(
                        agent_id="supervisor",
                        display_name="Orion",
                        mode="spelling",
                        state="completed",
                        summary="Supervisor selected the current spelling word.",
                        output=session.current_word,
                    )
                ],
                metadata={
                    "selected_agent": "spelling",
                    "target_word": session.current_word,
                    "exercise_level": session.level,
                    "spelling_phase": "word",
                    "evaluation_score": 0.0,
                    "evaluation_errors": [],
                    "next_focus": "Spell the target word letter by letter.",
                    "profile": _profile_to_metadata(profile),
                },
            )
        if session.awaiting_retry_decision:
            followup = self._spell.handle_followup(user_id, content, used_words=used_words)
            return OrchestrationResult(
                selected_mode="spelling",
                final_text=followup["message"],
                steps=[
                    AgentStep(
                        agent_id="supervisor",
                        display_name="Orion",
                        mode="spelling",
                        state="completed",
                        summary="Supervisor handled the next-step decision for spelling.",
                        output=followup["message"],
                    )
                ],
                metadata={
                    "selected_agent": "spelling",
                    "target_word": followup.get("target_word", ""),
                    "exercise_level": session.level,
                    "spelling_phase": "word",
                    "evaluation_score": 0.0,
                    "evaluation_errors": [],
                    "next_focus": "Spell the shown word carefully.",
                    "profile": _profile_to_metadata(profile),
                },
            )

        primary_result, primary_step = self._sub_agents["spelling"].run(
            self._router,
            content,
            context={"difficulty_level": profile.difficulty_level},
        )
        evaluation = self._spell.evaluate_spelling(user_id, content)
        final_text = (
            f"{evaluation['feedback']}\n\n"
            "Do you want to retry this word or move to the next one?"
        )
        updated_profile, evaluation_report, learning_note = self._memory.register_interaction(
            user_id=user_id,
            source=source,
            original_input=content,
            selected_mode="spelling",
            final_text=final_text,
            metadata={"target_word": evaluation["target_word"]},
        )
        metadata = {
            "selected_agent": "spelling",
            "feedback": primary_result.metadata.get("feedback", evaluation["feedback"]),
            "target_word": evaluation["target_word"],
            "recognized_word": evaluation["recognized_word"],
            "exercise_level": session.level,
            "spelling_phase": "feedback",
            "evaluation_score": 1.0 if evaluation["is_correct"] else 0.45,
            "evaluation_errors": [] if evaluation["is_correct"] else ["spelling-mismatch"],
            "next_focus": learning_note,
            "profile": _profile_to_metadata(updated_profile),
            "strengths": evaluation_report.strengths,
        }
        return OrchestrationResult(
            selected_mode="spelling",
            final_text=final_text,
            steps=[primary_step],
            metadata=metadata,
        )

    def _decide_route(
        self,
        content: str,
        preferred_mode: str | None,
        profile: UserProfile,
    ) -> RouteDecision:
        if preferred_mode and preferred_mode != "auto":
            return RouteDecision(
                mode=preferred_mode,
                reason=f"Supervisor accepted manual mode '{preferred_mode}'.",
            )

        lowered = content.lower()
        if any(token in lowered for token in ("grammar", "grammatical", "check grammar", "correct grammar")):
            return RouteDecision(
                mode="grammar",
                reason="Supervisor detected an explicit grammar evaluation request.",
            )
        if any(token in lowered for token in ("listen", "listening", "question about", "answer the question")):
            return RouteDecision(
                mode="listen",
                reason="Supervisor detected a listening-comprehension request.",
            )
        if any(token in lowered for token in ("spell", "spelling", "letters", "letter by letter")):
            return RouteDecision(
                mode="spelling",
                reason="Supervisor detected a spelling-oriented request.",
            )
        if any(token in lowered for token in ("say", "speak", "voice", "read aloud", "pronounce")):
            return RouteDecision(
                mode="tts",
                reason="Supervisor detected a speech playback request.",
            )
        return RouteDecision(
            mode="free",
            reason=(
                "Supervisor selected the conversation agent for correction flow. "
                f"Current learner level: {profile.difficulty_level}."
            ),
        )

    def _agent_for_mode(self, mode: str) -> SubAgent:
        for sub_agent in self._sub_agents.values():
            if sub_agent.routable and sub_agent.mode == mode:
                return sub_agent
        raise KeyError(f"No sub-agent available for mode '{mode}'")


def _profile_to_metadata(profile: UserProfile) -> dict[str, object]:
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
