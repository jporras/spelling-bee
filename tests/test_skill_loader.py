import tempfile
import unittest
import sys
from pathlib import Path

from src.application.services.skill_registry import SkillRegistry
from src.infrastructure.skill_loader import SkillLoader


class SkillLoaderTests(unittest.TestCase):
    def test_loader_keeps_running_when_one_skill_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            good = root / "good"
            bad = root / "bad"
            good.mkdir()
            bad.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            (good / "__init__.py").write_text("", encoding="utf-8")
            (bad / "__init__.py").write_text("", encoding="utf-8")
            (good / "module.py").write_text(
                "\n".join(
                    [
                        "from src.domain.entities import SkillResult",
                        "from src.domain.ports import Skill",
                        "class GoodSkill(Skill):",
                        "    name = 'good'",
                        "    supported_modes = ('good',)",
                        "    def execute(self, user_input):",
                        "        return SkillResult(content='ok')",
                        "def build():",
                        "    return GoodSkill()",
                    ]
                ),
                encoding="utf-8",
            )
            (bad / "module.py").write_text("def build():\n    raise RuntimeError('broken')\n", encoding="utf-8")

            registry = SkillRegistry()
            loader = SkillLoader(root)
            sys.path.insert(0, str(root.parent))
            try:
                loader.load_into(registry)
            finally:
                sys.path.remove(str(root.parent))

            self.assertEqual(registry.list_names(), ["good"])
            self.assertEqual(len(loader.errors), 1)


if __name__ == "__main__":
    unittest.main()
