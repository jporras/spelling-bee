from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities import SkillResult, UserInput


class Skill(ABC):
    name: str
    supported_modes: tuple[str, ...]

    @abstractmethod
    def execute(self, user_input: UserInput) -> SkillResult:
        raise NotImplementedError


class SpeechToTextPort(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError


class TextGenerationPort(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class SpeechSynthesisPort(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> dict[str, str]:
        raise NotImplementedError
