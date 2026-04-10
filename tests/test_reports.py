import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.ui.pyqt.reports import build_user_report_html, export_user_report_pdf


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_build_user_report_html_contains_core_sections(self) -> None:
        snapshot = {
            "profile": {
                "user_id": "jorge",
                "difficulty_level": "B1",
                "notes": ["Practice connectors."],
                "recent_errors": ["capitalization"],
            },
            "interaction_count": 4,
            "average_score": 0.82,
            "top_mode": "free",
            "last_session": {
                "selected_mode": "spelling",
                "evaluation_score": 0.75,
                "next_focus": "Review silent letters.",
                "summary": "Session checkpoint for jorge.",
            },
            "spelling_history": [{"word": "apple", "was_correct": True}],
            "mode_usage": {"grammar": 1, "talk": 2, "listen": 0, "spell": 1},
        }

        html = build_user_report_html(snapshot)

        self.assertIn("Whisper Learning Report", html)
        self.assertIn("jorge", html)
        self.assertIn("Practice connectors.", html)
        self.assertIn("apple", html)

    def test_export_user_report_pdf_creates_file(self) -> None:
        snapshot = {
            "profile": {"user_id": "jorge", "difficulty_level": "B1", "notes": [], "recent_errors": []},
            "interaction_count": 1,
            "average_score": 0.8,
            "top_mode": "free",
            "last_session": None,
            "spelling_history": [],
            "mode_usage": {},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "report.pdf"
            export_user_report_pdf(snapshot, target)
            self.assertTrue(target.exists())
            self.assertGreater(target.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
