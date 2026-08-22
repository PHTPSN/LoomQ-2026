[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $RepositoryRoot ".venv"
$Requirements = Join-Path $RepositoryRoot "starter_kit\requirements.txt"

$Python = Get-Command py -ErrorAction Stop
& $Python.Source -3.10 -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"

if (-not (Test-Path -LiteralPath $VirtualEnvironment)) {
    & $Python.Source -3.10 -m venv $VirtualEnvironment
}

$EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
& $EnvironmentPython -m pip install -r $Requirements

Write-Host "Environment ready: $VirtualEnvironment"
Write-Host "Activate with: .\scripts\activate.ps1"
