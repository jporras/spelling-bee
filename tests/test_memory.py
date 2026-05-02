import tempfile
import unittest
import sqlite3
from pathlib import Path

from src.application.memory.manager import MemoryManager
from src.infrastructure.persistence.user_store import UserStore


class MemoryManagerTests(unittest.TestCase):
    def test_register_interaction_updates_profile_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(UserStore(Path(temp_dir)))

            profile, report, note = memory.register_interaction(
                user_id="demo",
                source="text",
                original_input="this are wrong",
                selected_mode="free",
                final_text="This is wrong.",
            )

            self.assertEqual(profile.user_id, "demo")
            self.assertEqual(profile.total_interactions, 1)
            self.assertTrue(report.score > 0)
            self.assertTrue(note)
            self.assertEqual(memory.system_snapshot("demo")["interaction_count"], 1)

    def test_persist_exit_summary_updates_last_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(UserStore(Path(temp_dir)))
            memory.register_interaction(
                user_id="demo",
                source="text",
                original_input="this are wrong",
                selected_mode="free",
                final_text="This is wrong.",
            )

            snapshot = memory.persist_exit_summary("demo")

            self.assertIsNotNone(snapshot["last_session"])
            self.assertIn("Session checkpoint", snapshot["last_session"]["summary"])

    def test_mode_counters_track_distinct_practice_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(UserStore(Path(temp_dir)))

            memory.register_interaction("demo", "text", "hello", "grammar", "Hello.")
            memory.register_interaction("demo", "text", "repeat", "free", "Feedback.")
            memory.register_interaction("demo", "text", "answer", "listen", "Good.")

            profile = memory.load_profile("demo")

            self.assertEqual(profile.grammar_count, 1)
            self.assertEqual(profile.talk_count, 1)
            self.assertEqual(profile.listen_count, 1)
            self.assertEqual(profile.correction_count, 1)

    def test_spelling_history_uses_explicit_correctness_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(UserStore(Path(temp_dir)))

            memory.register_interaction(
                user_id="demo",
                source="text",
                original_input="a p l e",
                selected_mode="spelling",
                final_text="Not yet.",
                metadata={"target_word": "apple", "is_correct": False},
            )

            history = memory.system_snapshot("demo")["spelling_history"]

            self.assertEqual(history[0]["word"], "apple")
            self.assertFalse(history[0]["was_correct"])

    def test_existing_profile_database_gets_new_counter_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite3"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE profiles (
                    user_id TEXT PRIMARY KEY,
                    difficulty_level TEXT NOT NULL,
                    total_interactions INTEGER NOT NULL,
                    correction_count INTEGER NOT NULL,
                    spelling_count INTEGER NOT NULL,
                    pronunciation_count INTEGER NOT NULL,
                    recent_errors TEXT NOT NULL,
                    preferred_modes TEXT NOT NULL,
                    last_transcript TEXT NOT NULL,
                    notes TEXT NOT NULL
                );
                """
            )
            connection.commit()
            connection.close()

            store = UserStore(Path(temp_dir))
            profile = store.load_profile("demo")

            self.assertEqual(profile.grammar_count, 0)
            self.assertEqual(profile.talk_count, 0)
            self.assertEqual(profile.listen_count, 0)


if __name__ == "__main__":
    unittest.main()
