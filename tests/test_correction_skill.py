import unittest

from skills.correction.module import CorrectionSkill
from src.domain.entities import UserInput


class FakeLlm:
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt = ""

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


class CorrectionSkillTests(unittest.TestCase):
    def test_execute_returns_corrected_text_and_explanation(self) -> None:
        llm = FakeLlm(
            "CORRECTED: This is a sample sentence.\n"
            "EXPLANATION: Use 'is' because the subject is singular."
        )
        skill = CorrectionSkill(
            llm=llm,
            prompt_template="Fix the sentence.\nTEXT:\n{text}",
        )

        result = skill.execute(UserInput(content="this are a sample sentence", mode="free"))

        self.assertEqual(result.content, "This is a sample sentence.")
        self.assertEqual(
            result.metadata["explanation"],
            "Use 'is' because the subject is singular.",
        )
        self.assertIn("this are a sample sentence", llm.last_prompt)

    def test_parse_response_falls_back_when_sections_are_missing(self) -> None:
        corrected, explanation = CorrectionSkill._parse_response(
            "unexpected output",
            fallback="original text",
        )

        self.assertEqual(corrected, "original text")
        self.assertEqual(explanation, "No explanation returned.")


if __name__ == "__main__":
    unittest.main()
