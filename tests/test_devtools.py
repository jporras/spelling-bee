import tempfile
import unittest
from pathlib import Path

from src.devtools.scaffold import scaffold_adapter, scaffold_skill


class DevtoolsTests(unittest.TestCase):
    def test_scaffold_skill_creates_contract_and_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            files = scaffold_skill(root, "demo_skill", "Demo skill", "free")

            self.assertEqual(len(files), 2)
            self.assertTrue((root / "skills" / "demo_skill" / "SKILL.md").exists())
            self.assertTrue((root / "skills" / "demo_skill" / "module.py").exists())

    def test_scaffold_adapter_creates_python_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = scaffold_adapter(root, "demo_adapter", "custom")

            self.assertTrue(path.exists())
            self.assertIn("DemoAdapter", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
