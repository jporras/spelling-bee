import tempfile
import unittest
import wave
from pathlib import Path

from skills.transcription.module import TranscriptionSkill
from src.domain.entities import UserInput


class FakeStt:
    def transcribe(self, audio_path: str) -> str:
        return f"transcribed:{Path(audio_path).name}"


class TranscriptionSkillTests(unittest.TestCase):
    def test_transcription_skill_delegates_to_adapter(self) -> None:
        skill = TranscriptionSkill(stt=FakeStt())

        result = skill.execute(UserInput(content="sample.wav", mode="transcription"))

        self.assertEqual(result.content, "transcribed:sample.wav")
        self.assertEqual(result.metadata["source"], "faster-whisper")

    def test_placeholder_audio_file_can_be_created(self) -> None:
        from src.infrastructure.audio.microphone_recorder import MicrophoneRecorder

        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = MicrophoneRecorder(output_dir=Path(temp_dir))
            result = recorder.record(seconds=1)

            self.assertTrue(result.audio_path.exists())
            with wave.open(str(result.audio_path), "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), recorder.sample_rate)

    def test_recorder_supports_start_stop_and_cancel(self) -> None:
        from src.infrastructure.audio.microphone_recorder import MicrophoneRecorder

        with tempfile.TemporaryDirectory() as temp_dir:
            recorder = MicrophoneRecorder(output_dir=Path(temp_dir))
            start_message = recorder.start_recording()
            self.assertTrue(start_message)
            result = recorder.stop_recording()
            self.assertTrue(result.audio_path.exists())

            recorder.start_recording()
            pending_path = recorder._audio_path
            recorder.cancel_recording()
            if pending_path is not None:
                self.assertFalse(pending_path.exists())


if __name__ == "__main__":
    unittest.main()
