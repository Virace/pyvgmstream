$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot

try {
    & uv sync --reinstall-package pyvgmstream
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & uv build --wheel
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
