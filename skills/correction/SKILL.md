---
name: correction_skill
description: Correct English text, improve phrasing, and explain mistakes simply
input: text
output: corrected_text, explanation
supported_modes:
  - free
---

Task:
- Fix grammar and punctuation.
- Suggest a more natural phrasing.
- Explain the main mistakes at a B1-C1 level.

Implementation notes:
- Prefer concise corrections over rewriting everything.
- Preserve the learner's intent.
- Return both corrected text and short explanation metadata.
