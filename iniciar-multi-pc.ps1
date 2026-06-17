param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^node-[a-zA-Z0-9_-]+$")]
    [string]$NodeId,

    [Parameter(Mandatory = $true)]
    [string]$Peers,

    [Parameter(Mandatory = $true)]
    [string]$AuthSecret,

    [int]$NodePort = 8000,
    [int]$FrontendPort = 5173,
    [string]$NodeUrls = "",
    [switch]$WithFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($WithFrontend -and [string]::IsNullOrWhiteSpace($NodeUrls)) {
    throw "Informe -NodeUrls ao usar -WithFrontend."
}

$env:NODE_ID = $NodeId
$env:NODE_PORT = "$NodePort"
$env:PEERS = $Peers
$env:AUTH_SECRET = $AuthSecret
$env:NODE_URLS = $NodeUrls
$env:FRONTEND_PORT = "$FrontendPort"

Set-Location $projectRoot

$composeArguments = @(
    "compose",
    "-f",
    "docker-compose.multi-pc.yml"
)

if ($WithFrontend) {
    $composeArguments += @("--profile", "frontend")
}

$composeArguments += @("up", "--build", "-d")

Write-Host "Iniciando $NodeId em modo multi-PC..." -ForegroundColor Cyan
& docker @composeArguments
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao iniciar os containers."
}

Write-Host ""
docker compose -f docker-compose.multi-pc.yml ps
Write-Host ""
Write-Host "API local: http://localhost:$NodePort/docs" -ForegroundColor Green
Write-Host "Peers: $Peers"
if ($WithFrontend) {
    Write-Host "Frontend local: http://localhost:$FrontendPort" -ForegroundColor Green
    Write-Host "Nós exibidos: $NodeUrls"
}
