from __future__ import annotations

import os
from pathlib import Path

from src.domain.ports import TextGenerationPort
from src.infrastructure.llm.model_manager import ModelManager


class LlamaCppAdapter(TextGenerationPort):
    def __init__(
        self,
        model_path: str = "models/llama.gguf",
        n_ctx: int = 2048,
        temperature: float = 0.2,
        max_tokens: int = 256,
        auto_download: bool = True,
        hf_token: str = "",
        hf_model_repo: str = "",
        hf_model_file: str = "",
    ) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model_manager = ModelManager(
            target_path=model_path,
            auto_download=auto_download,
            hf_token=hf_token,
            hf_model_repo=hf_model_repo,
            hf_model_file=hf_model_file,
        )

    def generate(self, prompt: str) -> str:
        try:
            from llama_cpp import Llama
        except ImportError:
            return self._stub_response(prompt)

        model_file = self._model_manager.ensure_available()
        self.model_path = str(model_file)
        if not model_file.exists():
            return self._stub_response(prompt)

        llm = Llama(
            model_path=str(model_file),
            n_ctx=self.n_ctx,
            verbose=False,
        )
        output = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an English correction engine. "
                        "Return exactly two sections: "
                        "CORRECTED: <text> and EXPLANATION: <short explanation>."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return output["choices"][0]["message"]["content"].strip()

    def _stub_response(self, prompt: str) -> str:
        fallback_model = os.environ.get("LLAMA_CPP_MODEL", self.model_path)
        model_error = self._model_manager.last_error
        details = (
            f" Download error: {model_error}"
            if model_error
            else ""
        )
        return (
            "CORRECTED: "
            f"{self._extract_source_text(prompt)}\n"
            "EXPLANATION: "
            "Stub response. Add a GGUF model at "
            f"'{fallback_model}' to enable real corrections.{details}"
        )

    @staticmethod
    def _extract_source_text(prompt: str) -> str:
        marker = "TEXT:"
        if marker not in prompt:
            return prompt.strip()
        return prompt.split(marker, maxsplit=1)[1].strip()
