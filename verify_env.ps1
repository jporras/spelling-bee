$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

& $venvPython -c "import PyQt6, numpy, sounddevice, pyttsx3, faster_whisper, llama_cpp; print('all imports ok')"
& $venvPython -m unittest
