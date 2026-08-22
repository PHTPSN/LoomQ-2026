$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ActivationScript = Join-Path $RepositoryRoot ".venv\Scripts\Activate.ps1"
$EnvironmentFile = Join-Path $RepositoryRoot ".env"

if (-not (Test-Path -LiteralPath $ActivationScript)) {
    throw "Missing .venv. Run .\scripts\setup.ps1 first."
}

. $ActivationScript

if (Test-Path -LiteralPath $EnvironmentFile) {
    foreach ($Line in Get-Content -LiteralPath $EnvironmentFile -Encoding UTF8) {
        $Trimmed = $Line.Trim()
        if (-not $Trimmed -or $Trimmed.StartsWith("#")) {
            continue
        }

        $Name, $Value = $Trimmed -split "=", 2
        if ($Name -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            throw "Invalid environment variable name in .env: $Name"
        }

        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

if (-not $env:LOOMQ_LLM_API_KEY) {
    Write-Warning "LOOMQ_LLM_API_KEY is blank. Ask the user to provide it before running L2 model calls."
}

Write-Host "Python environment activated: $RepositoryRoot\.venv"
