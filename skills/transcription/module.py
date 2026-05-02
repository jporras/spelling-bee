from __future__ import annotations

from pathlib import Path

from src.domain.entities import SkillResult, UserInput
from src.domain.ports import Skill
from src.infrastructure.config import Settings
from src.infrastructure.runtime_paths import get_app_root, get_resource_root
from src.infrastructure.stt.faster_whisper_adapter import FasterWhisperAdapter


class TranscriptionSkill(Skill):
    name = "transcription_skill"
    supported_modes = ("transcription",)

    def __init__(self, stt: FasterWhisperAdapter) -> None:
        self._stt = stt

    def execute(self, user_input: UserInput) -> SkillResult:
        transcript = self._stt.transcribe(user_input.content.strip())
        return SkillResult(
            content=transcript,
            metadata={"source": "faster-whisper", "mode": user_input.mode},
        )


def build() -> TranscriptionSkill:
    default_root = Path(__file__).resolve().parents[2]
    settings = Settings.from_runtime(
        get_app_root(default_root),
        get_resource_root(default_root),
    )
    return TranscriptionSkill(
        stt=FasterWhisperAdapter(model_name=settings.faster_whisper_model)
    )
