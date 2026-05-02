# AOJ Command OS

AOJ Command OS is a local-first command system for airsoft field operations. It is built for a Raspberry Pi or laptop command node, a local router, browser clients on tablets or phones, and LoRa-connected field props.

## Stack

- Backend: FastAPI
- Frontend: React + Vite
- Database: SQLite
- Live updates: WebSockets
- Network model: local LAN only
- Hardware target: Raspberry Pi, Windows, or Linux host

## Project Layout

```text
backend/
frontend/
firmware/
scripts/
docs/
```

## Verified Runtime Status

The current codebase was smoke-tested with a live local runtime.

Verified:
- Backend startup
- Frontend build and preview startup
- Health check
- Mission Control routes and websocket state updates
- Schedule routes
- Results Board routes
- Prop Network mock commands
- System Logs routes
- System Monitor route
- AI Assistant mock route

## Quick Install

### Windows

Install dependencies and build the frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

Start both services in separate windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_aoj_windows.ps1
```

Or start them individually:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend_windows.ps1
```

### Linux

Make scripts executable, install dependencies, and build the frontend:

```bash
chmod +x ./scripts/*.sh
./scripts/install_linux.sh
```

Start both services in one shell session:

```bash
./scripts/start_aoj_linux.sh
```

Or start them individually:

```bash
./scripts/start_backend.sh
./scripts/start_frontend.sh
```

### Raspberry Pi

Use the Raspberry Pi specific installer if you want the Pi-oriented apt flow already included in the repo:

```bash
chmod +x ./scripts/*.sh
./scripts/install_pi.sh
./scripts/start_backend.sh
./scripts/start_frontend.sh
```

## Manual Development Run Commands

### Windows Backend

```powershell
Set-Location .\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Windows Frontend

Use `npm.cmd` in PowerShell if `npm` is blocked by execution policy:

```powershell
Set-Location .\frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

### Linux Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Linux Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Access URLs

- Frontend dev: http://127.0.0.1:5173
- Frontend preview or static: http://127.0.0.1:4173
- Backend API: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/api/health
- WebSocket: ws://127.0.0.1:8000/ws/live

## Installation System Overview

Cross-platform installer and launcher scripts included in the repo:

- Windows install: `scripts/install_windows.ps1`
- Windows backend start: `scripts/start_backend_windows.ps1`
- Windows frontend start: `scripts/start_frontend_windows.ps1`
- Windows combined launcher: `scripts/start_aoj_windows.ps1`
- Linux install: `scripts/install_linux.sh`
- Linux combined launcher: `scripts/start_aoj_linux.sh`
- Linux or Raspberry Pi backend start: `scripts/start_backend.sh`
- Linux or Raspberry Pi frontend start: `scripts/start_frontend.sh`

The installer scripts are intended for downloaded or unzipped copies of the project. They prepare the runtime in-place and do not require Docker.

## Field Notes

- Bind backend and frontend to `0.0.0.0` when serving other devices on the field LAN.
- Use the host machine or Raspberry Pi LAN IP for tablets and phones.
- Keep the deployment isolated from internet-facing networks during events.
- For detailed architecture, network, deployment, and protocol documentation, see `docs/`.
