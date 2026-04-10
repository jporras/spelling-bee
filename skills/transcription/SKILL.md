---
name: transcription_skill
description: Convert audio into text using a speech-to-text adapter
input: audio
output: transcription_text
supported_modes:
  - transcription
---

Task:
- Transcribe audio with Faster Whisper.
- Return transcript plus confidence metadata when available.
- Normalize whitespace for downstream skills.

Implementation notes:
- Keep the adapter swappable through a port.
- Avoid coupling STT details to the agent.
