[CmdletBinding()]
param(
    [ValidateSet("spinq", "originq", "braket", "all")]
    [string[]]$Backend = @("all")
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = Get-Command py -ErrorAction Stop

function Assert-NativeSuccess([string]$Action) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

$Selected = if ($Backend -contains "all") {
    @("spinq", "originq", "braket")
} else {
    $Backend | Select-Object -Unique
}

foreach ($Name in $Selected) {
    $VirtualEnvironment = Join-Path $RepositoryRoot ".venv-$Name"
    $Requirements = Join-Path $RepositoryRoot "requirements\$Name.lock.txt"

    $EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
    $EnvironmentIsValid = $false
    if (Test-Path -LiteralPath $EnvironmentPython -PathType Leaf) {
        & $EnvironmentPython -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"
        $EnvironmentIsValid = $LASTEXITCODE -eq 0
    }
    if (-not $EnvironmentIsValid) {
        & $Python.Source -3.10 -m venv --clear $VirtualEnvironment
        Assert-NativeSuccess "$Name virtual-environment creation"
    }

    & $EnvironmentPython -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"
    Assert-NativeSuccess "$Name Python 3.10 validation"
    & $EnvironmentPython -m pip install --no-cache-dir -r $Requirements
    Assert-NativeSuccess "$Name dependency installation"
    Write-Host "Backend environment ready: $Name ($VirtualEnvironment)"
}

$CorePython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $CorePython -PathType Leaf) {
    & $CorePython (Join-Path $PSScriptRoot "check-backends.py") @Selected
    Assert-NativeSuccess "Backend execution verification"
}
