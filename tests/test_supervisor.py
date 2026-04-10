import tempfile
import unittest
from pathlib import Path

from src.application.memory import MemoryManager
from src.application.supervisor import SupervisorAgent
from src.domain.entities import SkillResult, UserProfile
from src.infrastructure.persistence.user_store import UserStore


class FakeRouter:
    def route(
        self,
        content: str,
        mode: str = "free",
        context: dict[str, object] | None = None,
    ) -> SkillResult:
        if mode == "transcription":
            return SkillResult(
                content="this are a recorded sentence",
                metadata={"source": "fake-stt"},
            )
        if mode == "spelling":
            return SkillResult(
                content=content.upper(),
                metadata={"feedback": "Letters normalized."},
            )
        if mode == "tts":
            return SkillResult(
                content=f"Speak naturally: {content}",
                metadata={"voice": "default"},
            )
        return SkillResult(
            content=f"Corrected: {content}",
            metadata={"explanation": "Grammar reviewed."},
        )


class SupervisorAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = UserStore(Path(self.temp_dir.name))
        self.supervisor = SupervisorAgent(FakeRouter(), MemoryManager(self.store))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_auto_route_selects_spelling_agent(self) -> None:
        result = self.supervisor.handle("spell c a t", preferred_mode="auto", user_id="ana")

        self.assertEqual(result.selected_mode, "spelling")
        self.assertEqual(result.metadata["selected_agent"], "spelling")
        self.assertEqual(result.final_text, "SPELL C A T")
        self.assertEqual(result.metadata["profile"]["user_id"], "ana")

    def test_free_flow_adds_voice_preview(self) -> None:
        result = self.supervisor.handle("this are wrong", preferred_mode="auto", user_id="ana")

        self.assertEqual(result.selected_mode, "free")
        self.assertIn("voice_preview", result.metadata)
        self.assertEqual(result.metadata["selected_agent"], "conversation")
        self.assertEqual(result.steps[0].agent_id, "supervisor")
        self.assertEqual(result.steps[-1].agent_id, "learning")

    def test_audio_flow_runs_transcription_before_conversation(self) -> None:
        result = self.supervisor.handle_audio("recording.wav", preferred_mode="auto", user_id="ana")

        self.assertEqual(result.steps[1].agent_id, "transcription")
        self.assertEqual(result.metadata["transcript"], "this are a recorded sentence")
        self.assertEqual(result.selected_mode, "free")

    def test_user_snapshot_accumulates_interactions(self) -> None:
        self.supervisor.handle("this are wrong", preferred_mode="auto", user_id="ana")
        snapshot = self.supervisor.user_snapshot("ana")

        self.assertEqual(snapshot["interaction_count"], 1)
        self.assertEqual(snapshot["profile"]["total_interactions"], 1)

    def test_listen_mode_starts_with_passage_and_question(self) -> None:
        result = self.supervisor.handle("start", preferred_mode="listen", user_id="ana")

        self.assertEqual(result.selected_mode, "listen")
        self.assertEqual(result.metadata["listening_phase"], "question")
        self.assertTrue(result.metadata["expecting_response"])
        self.assertIn("Question:", result.final_text)

    def test_listen_mode_introduces_before_start(self) -> None:
        result = self.supervisor.handle("hello", preferred_mode="listen", user_id="ana")

        self.assertEqual(result.metadata["listening_phase"], "intro")
        self.assertIn("To begin, write: start", result.final_text)

    def test_listen_mode_second_turn_evaluates_answer(self) -> None:
        self.supervisor.handle("start", preferred_mode="listen", user_id="ana")
        result = self.supervisor.handle("She needed a book for her history class.", preferred_mode="listen", user_id="ana")

        self.assertEqual(result.selected_mode, "listen")
        self.assertEqual(result.metadata["listening_phase"], "feedback")
        self.assertFalse(result.metadata["expecting_response"])
        self.assertIn("Expected idea:", result.final_text)

    def test_talk_mode_starts_with_phrase(self) -> None:
        result = self.supervisor.handle("start", preferred_mode="free", user_id="ana")

        self.assertEqual(result.selected_mode, "free")
        self.assertEqual(result.metadata["talk_phase"], "prompt")
        self.assertIn("Repeat this phrase:", result.final_text)

    def test_spell_mode_intro_and_word_selection(self) -> None:
        intro = self.supervisor.handle("help", preferred_mode="spelling", user_id="ana")
        word = self.supervisor.handle("apple, window", preferred_mode="spelling", user_id="ana")

        self.assertEqual(intro.metadata["spelling_phase"], "choice")
        self.assertIn("Or write: start", intro.final_text)
        self.assertEqual(word.metadata["spelling_phase"], "word")
        self.assertEqual(word.metadata["target_word"], "apple")

    def test_spell_mode_start_suggests_word(self) -> None:
        result = self.supervisor.handle("start", preferred_mode="spelling", user_id="ana")

        self.assertEqual(result.metadata["spelling_phase"], "word")
        self.assertTrue(result.metadata["target_word"])

    def test_listen_mode_uses_profile_level_for_exercise(self) -> None:
        self.store.save_profile(UserProfile(user_id="pro", difficulty_level="C1"))

        result = self.supervisor.handle("start", preferred_mode="listen", user_id="pro")

        self.assertEqual(result.metadata["exercise_level"], "C1")

    def test_talk_mode_uses_profile_level_for_phrase(self) -> None:
        self.store.save_profile(UserProfile(user_id="beginner", difficulty_level="A2"))

        result = self.supervisor.handle("start", preferred_mode="free", user_id="beginner")

        self.assertEqual(result.metadata["exercise_level"], "A2")

    def test_snapshot_includes_last_session_and_spelling_memory(self) -> None:
        self.supervisor.handle("apple, window", preferred_mode="spelling", user_id="ana")
        self.supervisor.handle("a p p l e", preferred_mode="spelling", user_id="ana")
        snapshot = self.supervisor.user_snapshot("ana")

        self.assertIsNotNone(snapshot["last_session"])
        self.assertTrue(snapshot["spelling_history"])


if __name__ == "__main__":
    unittest.main()
