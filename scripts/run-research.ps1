$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Run uv sync --frozen --cache-dir .uv-cache in the project directory first.'
}
Push-Location -LiteralPath $projectDirectory
try {
    $screenConfig = if (Test-Path -LiteralPath 'screening.local.json') { 'screening.local.json' } else { 'screening.example.json' }
    & $projectPython -m stock_agent screen --config $screenConfig
    $screenExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $screenExit
