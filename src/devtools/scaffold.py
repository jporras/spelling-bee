from __future__ import annotations

from pathlib import Path


def scaffold_skill(root: Path, skill_name: str, description: str, mode: str) -> list[Path]:
    skill_dir = root / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    module_file = skill_dir / "module.py"
    skill_file.write_text(
        (
            f"---\nname: {skill_name}\ndescription: {description}\n"
            f"input: text\noutput: result\nsupported_modes:\n  - {mode}\n---\n\n"
            "Task:\n- Implement the skill behavior.\n"
        ),
        encoding="utf-8",
    )
    class_name = "".join(part.capitalize() for part in skill_name.split("_"))
    module_file.write_text(
        (
            "from src.domain.entities import SkillResult, UserInput\n"
            "from src.domain.ports import Skill\n\n\n"
            f"class {class_name}(Skill):\n"
            f"    name = \"{skill_name}\"\n"
            f"    supported_modes = (\"{mode}\",)\n\n"
            "    def execute(self, user_input: UserInput) -> SkillResult:\n"
            "        return SkillResult(content=user_input.content, metadata={\"status\": \"todo\"})\n\n\n"
            f"def build() -> {class_name}:\n"
            f"    return {class_name}()\n"
        ),
        encoding="utf-8",
    )
    return [skill_file, module_file]


def scaffold_adapter(root: Path, adapter_name: str, port_kind: str) -> Path:
    infra_dir = root / "src" / "infrastructure" / port_kind
    infra_dir.mkdir(parents=True, exist_ok=True)
    path = infra_dir / f"{adapter_name}.py"
    path.write_text(
        (
            "from __future__ import annotations\n\n"
            f"class {''.join(part.capitalize() for part in adapter_name.split('_'))}:\n"
            "    def __init__(self) -> None:\n"
            "        pass\n"
        ),
        encoding="utf-8",
    )
    return path
