[CmdletBinding()]
param(
    [ValidateSet("spinq", "originq", "braket", "all")]
    [string[]]$Backend = @("all")
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$Python = Get-Command py -ErrorAction Stop

$Selected = if ($Backend -contains "all") {
    @("spinq", "originq", "braket")
} else {
    $Backend | Select-Object -Unique
}

foreach ($Name in $Selected) {
    $VirtualEnvironment = Join-Path $RepositoryRoot ".venv-$Name"
    $Requirements = Join-Path $RepositoryRoot "requirements\$Name.lock.txt"

    if (-not (Test-Path -LiteralPath $VirtualEnvironment)) {
        & $Python.Source -3.10 -m venv $VirtualEnvironment
    }

    $EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
    & $EnvironmentPython -m pip install --no-cache-dir -r $Requirements
    Write-Host "Backend environment ready: $Name ($VirtualEnvironment)"
}
