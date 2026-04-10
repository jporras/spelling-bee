from __future__ import annotations

from pathlib import Path
from typing import Callable


class ModelManager:
    def __init__(
        self,
        target_path: str,
        auto_download: bool = True,
        hf_token: str = "",
        hf_model_repo: str = "",
        hf_model_file: str = "",
        api_factory: Callable[[], object] | None = None,
        download_fn: Callable[..., str] | None = None,
    ) -> None:
        self._target_path = Path(target_path)
        self._auto_download = auto_download
        self._hf_token = hf_token
        self._hf_model_repo = hf_model_repo
        self._hf_model_file = hf_model_file
        self._api_factory = api_factory
        self._download_fn = download_fn
        self.last_error = ""

    def ensure_available(self) -> Path:
        if self._target_path.exists():
            self.last_error = ""
            return self._target_path

        existing_ggufs = sorted(self._target_path.parent.glob("*.gguf"))
        if len(existing_ggufs) == 1:
            self.last_error = ""
            return existing_ggufs[0]

        if not self._auto_download or not self._hf_model_repo or not self._hf_token:
            return self._target_path

        api_factory = self._api_factory
        download_fn = self._download_fn
        if api_factory is None or download_fn is None:
            try:
                from huggingface_hub import HfApi, hf_hub_download
            except ImportError:
                return self._target_path
            api_factory = HfApi
            download_fn = hf_hub_download

        self._target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            filename = self._hf_model_file or self._discover_gguf_filename(api_factory)
        except Exception as exc:  # pragma: no cover - exact client exception varies by install
            self.last_error = str(exc)
            return self._target_path
        if not filename:
            return self._target_path

        try:
            downloaded = download_fn(
                repo_id=self._hf_model_repo,
                filename=filename,
                token=self._hf_token,
                local_dir=str(self._target_path.parent),
            )
        except Exception as exc:  # pragma: no cover - exact client exception varies by install
            self.last_error = str(exc)
            return self._target_path
        self.last_error = ""
        return Path(downloaded)

    def _discover_gguf_filename(self, api_factory: Callable[[], object]) -> str:
        api = api_factory()
        files = api.list_repo_files(repo_id=self._hf_model_repo, token=self._hf_token)
        for file_name in files:
            if file_name.lower().endswith(".gguf"):
                return file_name
        return ""
