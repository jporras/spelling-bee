from __future__ import annotations

import tempfile
import wave
from dataclasses import dataclass
from datetime import datetime
from os import close as close_fd
from pathlib import Path


@dataclass(slots=True)
class RecordingResult:
    audio_path: Path
    message: str


class MicrophoneRecorder:
    def __init__(
        self,
        output_dir: Path,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream = None
        self._frames: list[object] = []
        self._audio_path: Path | None = None
        self._started_at: datetime | None = None
        self._fallback_reason: str | None = None
        self.current_level = 0.0

    def record(self, seconds: int) -> RecordingResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            suffix=".wav",
            prefix="ukagaka_",
            dir=self.output_dir,
        )
        close_fd(fd)
        audio_path = Path(temp_path)

        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            self._write_silence(audio_path, seconds)
            return RecordingResult(
                audio_path=audio_path,
                message=(
                    "Audio dependencies missing. Created a silent placeholder file. "
                    "Install sounddevice and numpy for microphone capture."
                ),
            )

        try:
            frames = sd.rec(
                int(seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            sd.wait()
            audio = np.asarray(frames).tobytes()
        except Exception:
            self._write_silence(audio_path, seconds)
            return RecordingResult(
                audio_path=audio_path,
                message="Microphone capture failed. Created a silent placeholder file.",
            )
        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio)
        return RecordingResult(
            audio_path=audio_path,
            message=f"Recorded {seconds}s of audio to {audio_path.name}.",
        )

    def start_recording(self) -> str:
        if self._started_at is not None:
            return "Microphone capture is already active."

        self.output_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            suffix=".wav",
            prefix="ukagaka_",
            dir=self.output_dir,
        )
        close_fd(fd)
        self._audio_path = Path(temp_path)
        self._frames = []
        self._started_at = datetime.now()
        self._fallback_reason = None
        self.current_level = 0.0

        try:
            import sounddevice as sd
        except ImportError:
            self._fallback_reason = (
                "Audio dependencies missing. A silent placeholder file will be created when listening stops."
            )
            return "Listening started in fallback mode because audio dependencies are missing."

        try:
            def _callback(indata, frames, time, status) -> None:  # noqa: ANN001
                del frames, time
                if status:
                    self._fallback_reason = "Microphone stream reported a capture issue. A fallback file will be used."
                self._frames.append(indata.copy())
                try:
                    peak = abs(indata).max()
                    self.current_level = min(1.0, float(peak) / 32767.0)
                except Exception:
                    self.current_level = 0.0

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=_callback,
            )
            self._stream.start()
        except Exception:
            self._stream = None
            self._fallback_reason = "Microphone capture failed to start. A silent placeholder file will be created."
        return "Listening started. Click the microphone again to stop."

    def stop_recording(self) -> RecordingResult:
        if self._started_at is None or self._audio_path is None:
            raise RuntimeError("There is no active recording to stop.")

        audio_path = self._audio_path
        started_at = self._started_at
        stream = self._stream
        fallback_reason = self._fallback_reason

        self._audio_path = None
        self._started_at = None
        self._stream = None
        self.current_level = 0.0

        seconds = max(1, int((datetime.now() - started_at).total_seconds()))
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                fallback_reason = "Microphone capture could not stop cleanly. A silent placeholder file was created."

        if fallback_reason:
            self._write_silence(audio_path, seconds)
            self._frames = []
            return RecordingResult(
                audio_path=audio_path,
                message=fallback_reason,
            )

        try:
            import numpy as np
        except ImportError:
            self._write_silence(audio_path, seconds)
            self._frames = []
            return RecordingResult(
                audio_path=audio_path,
                message="NumPy is missing. Created a silent placeholder file.",
            )

        try:
            if self._frames:
                stacked = np.concatenate(self._frames, axis=0)
                audio = np.asarray(stacked, dtype="int16").tobytes()
            else:
                audio = b""
            if not audio:
                self._write_silence(audio_path, seconds)
                return RecordingResult(
                    audio_path=audio_path,
                    message="No audible input was captured. Created a silent placeholder file.",
                )
            with wave.open(str(audio_path), "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio)
            return RecordingResult(
                audio_path=audio_path,
                message=f"Recorded audio saved to {audio_path.name}.",
            )
        finally:
            self._frames = []

    def cancel_recording(self) -> None:
        if self._started_at is None or self._audio_path is None:
            return
        audio_path = self._audio_path
        stream = self._stream
        self._audio_path = None
        self._started_at = None
        self._stream = None
        self._frames = []
        self.current_level = 0.0
        self._fallback_reason = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        try:
            if audio_path.exists():
                audio_path.unlink()
        except OSError:
            pass

    def _write_silence(self, audio_path: Path, seconds: int) -> None:
        frame_count = seconds * self.sample_rate
        silence = b"\x00\x00" * frame_count * self.channels
        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(silence)
