import tempfile
import unittest
from pathlib import Path

from src.infrastructure.llm.model_manager import ModelManager


class FakeApi:
    def list_repo_files(self, repo_id: str, token: str) -> list[str]:
        del repo_id, token
        return ["notes.txt", "model-q4.gguf"]


class ModelManagerTests(unittest.TestCase):
    def test_returns_existing_file_without_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.gguf"
            model_path.write_text("ok", encoding="utf-8")
            manager = ModelManager(target_path=str(model_path))

            resolved = manager.ensure_available()

            self.assertEqual(resolved, model_path)

    def test_downloads_missing_model_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "missing.gguf"
            downloaded = Path(temp_dir) / "model-q4.gguf"

            def fake_download(repo_id: str, filename: str, token: str, local_dir: str) -> str:
                self.assertEqual(repo_id, "repo/model")
                self.assertEqual(filename, "model-q4.gguf")
                self.assertEqual(token, "token")
                self.assertEqual(local_dir, temp_dir)
                downloaded.write_text("ok", encoding="utf-8")
                return str(downloaded)

            manager = ModelManager(
                target_path=str(target),
                auto_download=True,
                hf_token="token",
                hf_model_repo="repo/model",
                api_factory=FakeApi,
                download_fn=fake_download,
            )

            resolved = manager.ensure_available()

            self.assertEqual(resolved, downloaded)
            self.assertTrue(downloaded.exists())


if __name__ == "__main__":
    unittest.main()
