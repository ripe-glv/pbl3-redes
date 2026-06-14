param(
    [Parameter(Mandatory = $true)][string]$NodeId,
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][string]$Peers,
    [string]$Python = "python"
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $projectRoot "backend"
$env:NODE_ID = $NodeId
$env:PORT = "$Port"
$env:PEERS = $Peers
$env:LEDGER_FILE = Join-Path $projectRoot "data\ledger-$NodeId.json"
$env:STORAGE_DIR = Join-Path $projectRoot "storage\$NodeId"
if (-not $env:POW_DIFFICULTY) {
    $env:POW_DIFFICULTY = "3"
}

Set-Location $backend
& $Python run.py
