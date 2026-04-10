Put one folder per character here.

Expected structure:

assets/
  characters/
    conversation/
      manifest.json
      idle.png
      active.png
      completed.png

Recommended agent folders:
- `conversation`
- `spelling`
- `transcription`
- `voice`
- `evaluation`
- `learning`

Each `manifest.json` should look like:

```json
{
  "states": {
    "idle": "idle.png",
    "active": "active.png",
    "completed": "completed.png"
  }
}
```

Use transparent PNG portraits sized around 800x1200 or similar.
