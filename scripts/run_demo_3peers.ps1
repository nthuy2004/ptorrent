# ==============================================================================
# pTorrent - Quick Startup Script for 3-Peer Demo on Single Machine
# ==============================================================================

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  pTorrent - 3-Peer Distributed Systems Demo Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Working directory: $Root"

# Clean up or prepare demo directories
$Peer1Dir = Join-Path $Root "demo\peer1_seeder"
$Peer2Dir = Join-Path $Root "demo\peer2_leecher1"
$Peer3Dir = Join-Path $Root "demo\peer3_leecher2"

New-Item -ItemType Directory -Force -Path $Peer1Dir | Out-Null
New-Item -ItemType Directory -Force -Path $Peer2Dir | Out-Null
New-Item -ItemType Directory -Force -Path $Peer3Dir | Out-Null

# Environment variable for local demo loopback
$env:PTORRENT_ADVERTISE_IP = "127.0.0.1"

Write-Host "Starting Peer 1 (Seeder) on port 6881..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; `$env:PTORRENT_ADVERTISE_IP='127.0.0.1'; python src/client/main.py --storage-root '$Peer1Dir' --port 6881"

Start-Sleep -Seconds 1

Write-Host "Starting Peer 2 (Leecher 1) on port 6882..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; `$env:PTORRENT_ADVERTISE_IP='127.0.0.1'; python src/client/main.py --storage-root '$Peer2Dir' --port 6882"

Start-Sleep -Seconds 1

Write-Host "Starting Peer 3 (Leecher 2) on port 6883..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; `$env:PTORRENT_ADVERTISE_IP='127.0.0.1'; python src/client/main.py --storage-root '$Peer3Dir' --port 6883"

Write-Host ""
Write-Host "All 3 peers launched successfully in separate processes!" -ForegroundColor Green
Write-Host "Demo Instructions:" -ForegroundColor Cyan
Write-Host "  1. On Peer 1: Click 'Create torrent' -> select a file -> share."
Write-Host "  2. On Peer 2: Click 'Open torrent' -> select the generated .ptorrent file."
Write-Host "  3. On Peer 3: Click 'Open torrent' -> select the generated .ptorrent file."
Write-Host "  4. Observe parallel downloading, cross-peer seeding, and live progress."
Write-Host "============================================================" -ForegroundColor Cyan
