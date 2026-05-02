from __future__ import annotations

from pathlib import Path

from src.domain.ports import SpeechToTextPort


class FasterWhisperAdapter(SpeechToTextPort):
    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._model = None

    def transcribe(self, audio_path: str) -> str:
        audio_file = Path(audio_path)
        if not audio_file.exists():
            return f"[missing-audio] {audio_file}"

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return (
                f"[stub transcription] File '{audio_file.name}' queued for model "
                f"'{self.model_name}'. Install faster-whisper for real STT."
            )

        model = self._get_model(WhisperModel)
        segments, info = model.transcribe(str(audio_file))
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        if transcript:
            return transcript
        return f"[empty transcription] language={getattr(info, 'language', 'unknown')}"

    def _get_model(self, model_factory):
        if self._model is None:
            self._model = model_factory(self.model_name)
        return self._model
