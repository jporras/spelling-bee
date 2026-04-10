---
name: tts_skill
description: Convert generated responses into speech-ready output
input: text
output: audio_instruction, voice_metadata
supported_modes:
  - tts
---

Task:
- Prepare text for TTS playback.
- Add voice and pacing metadata.
- Keep utterances short and natural for the ukagaka UI.

Implementation notes:
- Start with formatting and metadata before wiring a real TTS engine.
