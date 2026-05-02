import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
