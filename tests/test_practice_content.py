import unittest

from src.application.modes.practice_content import load_practice_content


class PracticeContentTests(unittest.TestCase):
    def test_default_practice_content_loads_all_modes(self) -> None:
        content = load_practice_content()

        self.assertIn("B1", content.talk_phrases)
        self.assertIn("B1", content.listening_exercises)
        self.assertIn("B1", content.spelling_words)
        self.assertTrue(content.talk_phrases["B1"])
        self.assertTrue(content.listening_exercises["B1"])
        self.assertTrue(content.spelling_words["B1"])


if __name__ == "__main__":
    unittest.main()
