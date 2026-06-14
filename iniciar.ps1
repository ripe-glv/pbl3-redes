$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $projectRoot

Write-Host "Iniciando Sentinel Ledger..." -ForegroundColor Cyan
docker compose up --build -d

Write-Host ""
docker compose ps
Write-Host ""
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "API node-a: http://localhost:8001/docs"
Write-Host "API node-b: http://localhost:8002/docs"
Write-Host "API node-c: http://localhost:8003/docs"

