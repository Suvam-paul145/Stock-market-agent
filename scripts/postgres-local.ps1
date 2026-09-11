# Dedicated local database only; this script never changes a hosted database.
[CmdletBinding()]
param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Start'
)

$ErrorActionPreference = 'Stop'
$composeFile = Join-Path (Split-Path -Parent $PSScriptRoot) 'compose.yaml'
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCommand) {
    $dockerPath = Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'
    if (-not (Test-Path -LiteralPath $dockerPath)) {
        throw 'Docker Desktop is required. Install and start it, then run this script again.'
    }
} else {
    $dockerPath = $dockerCommand.Source
}

switch ($Action) {
    'Start' {
        & $dockerPath compose --file $composeFile up --detach --wait --wait-timeout 90 postgres
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed. Check that Docker Desktop is running and port 55432 is free.' }
        Write-Host 'Local PostgreSQL is ready. Development-only connection string:'
        Write-Host 'postgresql://stock_agent_dev:local-development-only@127.0.0.1:55432/stock_agent_test'
        Write-Host 'Data persists in the stock-agent-dev_postgres-data Docker volume.'
    }
    'Stop' {
        & $dockerPath compose --file $composeFile stop postgres
        if ($LASTEXITCODE -ne 0) { throw 'Could not stop the project PostgreSQL container.' }
        Write-Host 'Stopped the project database. Its data volume is preserved.'
    }
    'Status' {
        & $dockerPath compose --file $composeFile ps postgres
        if ($LASTEXITCODE -ne 0) { throw 'Could not read the project PostgreSQL status.' }
    }
}
