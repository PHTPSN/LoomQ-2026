[CmdletBinding()]
param(
    [ValidateRange(0, 65535)]
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$CorePython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
$Backends = @("spinq", "originq", "braket")
$NeedsSetup = -not (Test-Path -LiteralPath $CorePython -PathType Leaf)

if (-not $NeedsSetup) {
    foreach ($Name in $Backends) {
        $BackendPython = Join-Path $RepositoryRoot ".venv-$Name\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $BackendPython -PathType Leaf)) {
            $NeedsSetup = $true
            break
        }
    }
}

if (-not $NeedsSetup) {
    & $CorePython (Join-Path $PSScriptRoot "check-backends.py") @Backends
    $NeedsSetup = $LASTEXITCODE -ne 0
}

if ($NeedsSetup) {
    Write-Host "Preparing the Python 3.10 core and three local backends..."
    & (Join-Path $PSScriptRoot "setup.ps1")
}

Set-Location -LiteralPath $RepositoryRoot
& $CorePython -m starter_kit.loomq_l2.ui_server --port $Port
