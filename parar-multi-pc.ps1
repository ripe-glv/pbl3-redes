$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# O Compose exige estas variáveis para "up". Valores neutros permitem que
# "down" seja executado em outro terminal sem precisar repetir a configuração.
$env:NODE_ID = "node-stop"
$env:PEERS = "http://127.0.0.1:1"
$env:AUTH_SECRET = "stop-only"

Set-Location $projectRoot
docker compose -f docker-compose.multi-pc.yml down
