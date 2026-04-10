from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    base_dir: Path
    skills_dir: Path
    llama_model_path: str
    llama_n_ctx: int
    llama_temperature: float
    llama_max_tokens: int
    faster_whisper_model: str
    recording_duration_seconds: int
    recordings_dir: Path
    data_dir: Path
    tts_voice_name: str
    tts_rate: int
    auto_download_model: bool
    hf_token: str
    hf_model_repo: str
    hf_model_file: str
    ui_theme: str
    app_user_name: str

    @classmethod
    def from_project_root(cls, root: Path) -> "Settings":
        _load_dotenv(root / ".env")
        return cls(
            base_dir=root,
            skills_dir=root / "skills",
            llama_model_path=os.environ.get("LLAMA_CPP_MODEL", "models/llama.gguf"),
            llama_n_ctx=int(os.environ.get("LLAMA_CPP_N_CTX", "2048")),
            llama_temperature=float(os.environ.get("LLAMA_CPP_TEMPERATURE", "0.2")),
            llama_max_tokens=int(os.environ.get("LLAMA_CPP_MAX_TOKENS", "256")),
            faster_whisper_model=os.environ.get("FASTER_WHISPER_MODEL", "base"),
            recording_duration_seconds=int(os.environ.get("RECORDING_DURATION_SECONDS", "4")),
            recordings_dir=root / "runtime" / "recordings",
            data_dir=root / "runtime" / "data",
            tts_voice_name=os.environ.get("TTS_VOICE_NAME", "default"),
            tts_rate=int(os.environ.get("TTS_RATE", "180")),
            auto_download_model=os.environ.get("AUTO_DOWNLOAD_MODEL", "true").lower() == "true",
            hf_token=os.environ.get("HF_TOKEN", ""),
            hf_model_repo=os.environ.get("HF_MODEL_REPO", "google/gemma-3-4b-it-qat-q4_0-gguf"),
            hf_model_file=os.environ.get("HF_MODEL_FILE", ""),
            ui_theme=os.environ.get("UI_THEME", "cream"),
            app_user_name=os.environ.get("APP_USER_NAME", "guest"),
        )


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)
