from __future__ import annotations

from dataclasses import dataclass

from src.domain.ports import Skill


@dataclass(slots=True)
class RegisteredSkill:
    name: str
    instance: Skill
    supported_modes: tuple[str, ...]


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, RegisteredSkill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = RegisteredSkill(
            name=skill.name,
            instance=skill,
            supported_modes=skill.supported_modes,
        )

    def resolve(self, mode: str) -> Skill:
        for entry in self._skills.values():
            if mode in entry.supported_modes:
                return entry.instance
        raise KeyError(f"No skill registered for mode '{mode}'")

    def list_names(self) -> list[str]:
        return sorted(self._skills.keys())
