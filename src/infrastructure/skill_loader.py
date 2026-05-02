from __future__ import annotations

from importlib import import_module
from pathlib import Path

from src.application.skill_registry import SkillRegistry


class SkillLoader:
    FALLBACK_MODULES = (
        "skills.correction.module",
        "skills.spelling.module",
        "skills.transcription.module",
        "skills.tts.module",
    )

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir

    def load_into(self, registry: SkillRegistry) -> None:
        if not self._skills_dir.exists():
            for module_name in self.FALLBACK_MODULES:
                module = import_module(module_name)
                skill = module.build()
                registry.register(skill)
            return

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            module_path = skill_dir / "module.py"
            if not module_path.exists():
                continue

            module_name = ".".join(
                module_path.relative_to(self._skills_dir.parent).with_suffix("").parts
            )
            module = import_module(module_name)
            skill = module.build()
            registry.register(skill)
