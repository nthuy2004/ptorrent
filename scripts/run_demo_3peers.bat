@echo off
rem ==============================================================================
rem pTorrent - Quick Startup Batch Script for 3-Peer Demo
rem ==============================================================================

cd /d "%~dp0\.."

set PTORRENT_ADVERTISE_IP=127.0.0.1

echo Starting Peer 1 (Seeder) on port 6881...
start "pTorrent - Peer 1 (Seeder 6881)" cmd /k "set PTORRENT_ADVERTISE_IP=127.0.0.1 && python src\client\main.py --storage-root demo\peer1_seeder --port 6881"

timeout /t 1 /nobreak >nul

echo Starting Peer 2 (Leecher 1) on port 6882...
start "pTorrent - Peer 2 (Leecher 6882)" cmd /k "set PTORRENT_ADVERTISE_IP=127.0.0.1 && python src\client\main.py --storage-root demo\peer2_leecher1 --port 6882"

timeout /t 1 /nobreak >nul

echo Starting Peer 3 (Leecher 2) on port 6883...
start "pTorrent - Peer 3 (Leecher 6883)" cmd /k "set PTORRENT_ADVERTISE_IP=127.0.0.1 && python src\client\main.py --storage-root demo\peer3_leecher2 --port 6883"

echo.
echo All 3 peers launched successfully!
