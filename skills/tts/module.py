from __future__ import annotations

from pathlib import Path

from src.domain.entities import SkillResult, UserInput
from src.domain.ports import Skill
from src.infrastructure.config import Settings
from src.infrastructure.tts.pyttsx3_adapter import Pyttsx3Adapter


class TtsSkill(Skill):
    name = "tts_skill"
    supported_modes = ("tts",)

    def __init__(self, tts: Pyttsx3Adapter) -> None:
        self._tts = tts

    def execute(self, user_input: UserInput) -> SkillResult:
        synthesis = self._tts.synthesize(user_input.content.strip())
        return SkillResult(
            content=synthesis["preview"],
            metadata={
                "voice": synthesis["voice"],
                "tts_status": synthesis["status"],
                "mode": user_input.mode,
            },
        )


def build() -> TtsSkill:
    root = Path(__file__).resolve().parents[2]
    settings = Settings.from_project_root(root)
    return TtsSkill(
        tts=Pyttsx3Adapter(
            voice_name=settings.tts_voice_name,
            rate=settings.tts_rate,
        )
    )
