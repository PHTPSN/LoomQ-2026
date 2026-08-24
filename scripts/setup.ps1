[CmdletBinding()]
param(
    [switch]$SkipBackends
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $RepositoryRoot ".venv"
$Requirements = Join-Path $RepositoryRoot "starter_kit\requirements.txt"

function Assert-NativeSuccess([string]$Action) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

$Python = Get-Command py -ErrorAction Stop
& $Python.Source -3.10 -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"
Assert-NativeSuccess "Python 3.10 validation"

$EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
$EnvironmentIsValid = $false
if (Test-Path -LiteralPath $EnvironmentPython -PathType Leaf) {
    & $EnvironmentPython -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"
    $EnvironmentIsValid = $LASTEXITCODE -eq 0
}
if (-not $EnvironmentIsValid) {
    & $Python.Source -3.10 -m venv --clear $VirtualEnvironment
    Assert-NativeSuccess "Core virtual-environment creation"
}

& $EnvironmentPython -m pip install -r $Requirements
Assert-NativeSuccess "Core dependency installation"

$EnvironmentFile = Join-Path $RepositoryRoot ".env"
$EnvironmentTemplate = Join-Path $RepositoryRoot ".env.example"
if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    Copy-Item -LiteralPath $EnvironmentTemplate -Destination $EnvironmentFile
    Write-Host "Created local configuration from .env.example"
}

if (-not $SkipBackends) {
    & (Join-Path $PSScriptRoot "setup-backends.ps1") -Backend all
}

Write-Host "Environment ready: $VirtualEnvironment"
Write-Host "Activate with: .\scripts\activate.ps1"
