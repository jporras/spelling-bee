param(
    [string]$VenvPath = ".venv",
    [string]$AppName = "WhisperUkagaka"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot "$VenvPath\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found at $VenvPath. Run .\setup.ps1 first."
}

Write-Host "Installing PyInstaller in $VenvPath"
& $venvPython -m pip install pyinstaller

$distDir = Join-Path $projectRoot "dist"
$buildDir = Join-Path $projectRoot "build"

if (Test-Path $distDir) {
    Remove-Item -Recurse -Force -LiteralPath $distDir
}
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force -LiteralPath $buildDir
}

Write-Host "Building Windows executable"
& $venvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name $AppName `
    --add-data "assets;assets" `
    --add-data "prompts;prompts" `
    --add-data "themes;themes" `
    --add-data "skills;skills" `
    --add-data ".env.example;." `
    --hidden-import "skills.correction.module" `
    --hidden-import "skills.spelling.module" `
    --hidden-import "skills.transcription.module" `
    --hidden-import "skills.tts.module" `
    (Join-Path $projectRoot "main.py")

$outputDir = Join-Path $distDir $AppName
$runtimeDir = Join-Path $outputDir "runtime"
$modelsDir = Join-Path $outputDir "models"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runtimeDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runtimeDir "recordings") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runtimeDir "reports") | Out-Null
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null

if (-not (Test-Path (Join-Path $outputDir ".env"))) {
    Copy-Item (Join-Path $projectRoot ".env.example") (Join-Path $outputDir ".env")
}

Write-Host "Build complete: $outputDir"
Write-Host "Edit $outputDir\.env before first launch if you need a different model or Hugging Face token."
