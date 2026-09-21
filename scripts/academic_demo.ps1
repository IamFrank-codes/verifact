[CmdletBinding()]
param(
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ComposeFiles = @('-f', 'docker-compose.yml', '-f', 'docker-compose.academic.yml')
$EnvFile = 'backend/.env'

Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker was not found. Install Docker Desktop and try again.'
}

& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Compose is unavailable. Confirm that Docker Desktop is running.'
}

if (-not (Test-Path $EnvFile)) {
    throw "Missing $EnvFile. Create it from backend/.env.example and add your private credentials."
}

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose @ComposeFiles --env-file $EnvFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed with exit code $LASTEXITCODE."
    }
}

switch ($Action) {
    'start' {
        Write-Host 'Validating the academic Docker configuration...'
        Invoke-Compose @('config') *> $null
        Write-Host 'Starting VeriFact with Supabase and live external APIs...'
        Invoke-Compose @('up', '--build', '-d')
        Write-Host ''
        Write-Host 'VeriFact is available at http://localhost:5173'
        Write-Host 'API health: http://localhost:8000/health'
        Write-Host 'Use .\scripts\academic_demo.ps1 -Action logs to view API logs.'
    }
    'stop' {
        Write-Host 'Stopping the VeriFact academic demo...'
        Invoke-Compose @('down')
    }
    'restart' {
        Write-Host 'Restarting the VeriFact academic demo...'
        Invoke-Compose @('down')
        Invoke-Compose @('up', '--build', '-d')
    }
    'status' {
        Invoke-Compose @('ps')
    }
    'logs' {
        Invoke-Compose @('logs', '-f', '--tail=100', 'verifact-api')
    }
}
