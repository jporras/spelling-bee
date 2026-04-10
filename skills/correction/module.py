from __future__ import annotations

from pathlib import Path

from src.domain.entities import SkillResult, UserInput
from src.domain.ports import Skill
from src.infrastructure.config import Settings
from src.infrastructure.llm.llama_cpp_adapter import LlamaCppAdapter


class CorrectionSkill(Skill):
    name = "correction_skill"
    supported_modes = ("free", "grammar")

    def __init__(self, llm: LlamaCppAdapter, prompt_template: str) -> None:
        self._llm = llm
        self._prompt_template = prompt_template

    def execute(self, user_input: UserInput) -> SkillResult:
        source_text = user_input.content.strip()
        prompt = self._prompt_template.format(text=source_text)
        raw_output = self._llm.generate(prompt)
        corrected, explanation = self._parse_response(raw_output, fallback=source_text)
        return SkillResult(
            content=corrected,
            metadata={"explanation": explanation, "mode": user_input.mode},
        )

    @staticmethod
    def _parse_response(raw_output: str, fallback: str) -> tuple[str, str]:
        corrected = fallback
        explanation = "No explanation returned."

        for line in raw_output.splitlines():
            stripped = line.strip()
            if stripped.startswith("CORRECTED:"):
                corrected = stripped.removeprefix("CORRECTED:").strip() or fallback
            if stripped.startswith("EXPLANATION:"):
                explanation = stripped.removeprefix("EXPLANATION:").strip() or explanation

        return corrected, explanation


def build() -> CorrectionSkill:
    root = Path(__file__).resolve().parents[2]
    settings = Settings.from_project_root(root)
    prompt_template = (root / "prompts" / "correction_prompt.txt").read_text(
        encoding="utf-8"
    )
    llm = LlamaCppAdapter(
        model_path=settings.llama_model_path,
        n_ctx=settings.llama_n_ctx,
        temperature=settings.llama_temperature,
        max_tokens=settings.llama_max_tokens,
        auto_download=settings.auto_download_model,
        hf_token=settings.hf_token,
        hf_model_repo=settings.hf_model_repo,
        hf_model_file=settings.hf_model_file,
    )
    return CorrectionSkill(llm=llm, prompt_template=prompt_template)
