param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot "$VenvPath\\Scripts\\python.exe"
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

Write-Host "Creating virtual environment at $VenvPath"
python -m venv (Join-Path $projectRoot $VenvPath)

Write-Host "Installing base dependencies"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")

if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($vsPath) {
        $vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
        if (Test-Path $vcvars) {
            Write-Host "Installing llama-cpp-python with Visual Studio build tools"
            $cmd = "call `"$vcvars`" && `"$venvPython`" -m pip install --force-reinstall llama-cpp-python"
            cmd /c $cmd
        }
    }
}

Write-Host "Verifying environment"
& $venvPython -m unittest
Write-Host "Done. Activate with: .\$VenvPath\Scripts\Activate.ps1"
