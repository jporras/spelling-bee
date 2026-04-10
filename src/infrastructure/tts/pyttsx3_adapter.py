from __future__ import annotations

from threading import Lock

from src.domain.ports import SpeechSynthesisPort


class Pyttsx3Adapter(SpeechSynthesisPort):
    _engine = None
    _engine_lock = Lock()

    def __init__(self, voice_name: str = "default", rate: int = 180) -> None:
        self.voice_name = voice_name
        self.rate = rate

    def synthesize(self, text: str) -> dict[str, str]:
        try:
            import pyttsx3
        except ImportError:
            return {
                "status": "stub",
                "voice": self.voice_name,
                "preview": f"Speak naturally: {text}",
            }

        with self._engine_lock:
            try:
                engine = self._get_engine(pyttsx3)
                try:
                    engine.stop()
                except RuntimeError:
                    pass

                engine.setProperty("rate", self.rate)
                if self.voice_name != "default":
                    for voice in engine.getProperty("voices"):
                        if self.voice_name.lower() in voice.name.lower():
                            engine.setProperty("voice", voice.id)
                            break
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:  # noqa: BLE001
                type(self)._engine = None
                return {
                    "status": "fallback",
                    "voice": self.voice_name,
                    "preview": f"Speak naturally: {text}",
                    "error": str(exc),
                }
        return {
            "status": "spoken",
            "voice": self.voice_name,
            "preview": f"Spoken with rate {self.rate}: {text}",
        }

    @classmethod
    def _get_engine(cls, pyttsx3_module):
        if cls._engine is None:
            cls._engine = pyttsx3_module.init()
        return cls._engine
