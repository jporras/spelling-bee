import tempfile
import unittest
from pathlib import Path

from src.infrastructure.llm.llama_cpp_adapter import LlamaCppAdapter
from src.infrastructure.stt.faster_whisper_adapter import FasterWhisperAdapter


class FakeLlama:
    instances = 0

    def __init__(self, model_path: str, n_ctx: int, verbose: bool) -> None:
        del model_path, n_ctx, verbose
        type(self).instances += 1


class FakeWhisperModel:
    instances = 0

    def __init__(self, model_name: str) -> None:
        del model_name
        type(self).instances += 1


class AdapterCachingTests(unittest.TestCase):
    def test_llama_adapter_reuses_loaded_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.gguf"
            model_path.write_text("ok", encoding="utf-8")
            adapter = LlamaCppAdapter(model_path=str(model_path))
            FakeLlama.instances = 0

            first = adapter._get_llm(FakeLlama, model_path)
            second = adapter._get_llm(FakeLlama, model_path)

            self.assertIs(first, second)
            self.assertEqual(FakeLlama.instances, 1)

    def test_faster_whisper_adapter_reuses_loaded_model(self) -> None:
        adapter = FasterWhisperAdapter(model_name="base")
        FakeWhisperModel.instances = 0

        first = adapter._get_model(FakeWhisperModel)
        second = adapter._get_model(FakeWhisperModel)

        self.assertIs(first, second)
        self.assertEqual(FakeWhisperModel.instances, 1)


if __name__ == "__main__":
    unittest.main()
