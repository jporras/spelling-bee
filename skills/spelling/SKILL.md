---
name: spelling_skill
description: Parse dictated spelling attempts and validate letter-by-letter output
input: transcription_text
output: normalized_spelling, validation_feedback
supported_modes:
  - spelling
---

Task:
- Parse spelled words from noisy speech-to-text output.
- Normalize separators, pauses, and repeated letters.
- Validate the intended spelling and return feedback.

Implementation notes:
- Be robust to Whisper transcription artifacts.
- Prefer deterministic parsing before calling an LLM.
