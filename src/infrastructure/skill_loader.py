from __future__ import annotations

from importlib import import_module
from pathlib import Path

from src.application.services.skill_registry import SkillRegistry


class SkillLoader:
    FALLBACK_MODULES = (
        "skills.correction.module",
        "skills.spelling.module",
        "skills.transcription.module",
        "skills.tts.module",
    )

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir
        self.errors: list[str] = []

    def load_into(self, registry: SkillRegistry) -> None:
        self.errors = []
        if not self._skills_dir.exists():
            for module_name in self.FALLBACK_MODULES:
                self._load_module_into(registry, module_name)
            return

        for skill_dir in sorted(self._skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            module_path = skill_dir / "module.py"
            if not module_path.exists():
                continue

            module_name = ".".join(
                module_path.relative_to(self._skills_dir.parent).with_suffix("").parts
            )
            self._load_module_into(registry, module_name)

    def _load_module_into(self, registry: SkillRegistry, module_name: str) -> None:
        try:
            module = import_module(module_name)
            skill = module.build()
            registry.register(skill)
        except Exception as exc:  # noqa: BLE001
            self.errors.append(f"{module_name}: {exc}")
