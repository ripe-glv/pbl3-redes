param(
    [ValidatePattern("^node-[a-zA-Z0-9_-]+$")]
    [string]$NodeId = "",

    [string]$Peers = "",

    [int]$NodePort = 8000,
    [int]$FrontendPort = 5173,
    [string]$NodeUrls = "http://172.16.103.7:8000,http://172.16.103.9:8000,http://172.16.103.10:8000",
    [switch]$WithFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$topology = [ordered]@{
    "172.16.103.7"  = "node-a"
    "172.16.103.9"  = "node-b"
    "172.16.103.10" = "node-c"
}

$localIp = @(
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $topology.Contains($_.IPAddress) } |
        Select-Object -ExpandProperty IPAddress
) | Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($NodeId)) {
    if (-not $localIp) {
        throw "Este computador não possui um dos IPs configurados: $($topology.Keys -join ', '). Informe -NodeId e -Peers manualmente."
    }
    $NodeId = $topology[$localIp]
}

if ([string]::IsNullOrWhiteSpace($Peers)) {
    if (-not $localIp) {
        throw "Não foi possível determinar os peers. Informe -Peers manualmente."
    }
    $Peers = @(
        $topology.Keys |
            Where-Object { $_ -ne $localIp } |
            ForEach-Object { "http://${_}:8000" }
    ) -join ","
}

$startFrontend = $WithFrontend -or ($localIp -eq "172.16.103.7")

$env:NODE_ID = $NodeId
$env:NODE_PORT = "$NodePort"
$env:PEERS = $Peers
$env:NODE_URLS = $NodeUrls
$env:FRONTEND_PORT = "$FrontendPort"

Set-Location $projectRoot

$composeArguments = @(
    "compose",
    "-f",
    "docker-compose.multi-pc.yml"
)

if ($startFrontend) {
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
if ($localIp) {
    Write-Host "API local: http://${localIp}:$NodePort/docs" -ForegroundColor Green
} else {
    Write-Host "API local: http://localhost:$NodePort/docs" -ForegroundColor Green
}
Write-Host "Peers: $Peers"
if ($startFrontend) {
    Write-Host "Frontend: http://172.16.103.7:$FrontendPort" -ForegroundColor Green
    Write-Host "Nós exibidos: $NodeUrls"
}
