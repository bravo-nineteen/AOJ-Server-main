# AOJ Command OS

AOJ Command OS is a local-first command system for airsoft field operations. It runs on a Raspberry Pi or Windows laptop as a command node, connects to a local router, and serves browser clients on tablets or phones. LoRa-connected field props communicate over RF.

## Stack

| Component | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | React 18 + Vite |
| Live updates | WebSockets |
| AI Advisor | Conversational rules engine (mock; LLM-swappable) |
| Network | Local LAN only |
| Hardware target | Raspberry Pi, Windows PC, or Linux host |

## Features

- **Mission Control** — create missions, start/pause/end games, live timers and scores
- **AI Assistant** — conversational advisor for game suggestions, rule building, briefings, and diagnostics. Asks for confirmation before operational actions.
- **Custom Teams & Game Modes** — no-code builder for team names and game rule sets
- **Knowledge Base** — feed the AI with your field rules, custom modes, and team info
- **Prop Network** — manage and monitor LoRa-connected field props (non-hardware mock in dev)
- **Schedule & Results Board** — event timeline and session history
- **Theme Editor** — runtime CSS theme customisation
- **System Monitor & Logs** — telemetry, audit logs, and update center

---

## Quick Install — Windows

### Requirements

| Software | Minimum Version | Download |
|---|---|---|
| Python | 3.11 | https://python.org/downloads |
| Node.js | 18 | https://nodejs.org |
| Git (optional) | any | https://git-scm.com |

### Installer Method A — EXE Setup (easiest)

1. Download the Windows installer EXE from Releases (example: `AOJ_Command_OS_Setup_1.0.0.exe`).
2. Double-click the installer and follow the wizard.
3. Keep default install path unless you need a custom location.
4. When installation completes, launch AOJ Command OS from Start Menu.
5. Open `http://localhost:8000` if browser does not auto-open.

### Installer Method B — Script Install (power users)

Open **PowerShell as Administrator**, then:

```powershell
# 1. Clone or download and extract the project
git clone https://github.com/YOUR_ORG/AOJ-Server.git
Set-Location AOJ-Server

# 2. Install all dependencies and build the frontend
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

The installer:
- Creates a Python virtual environment at `backend\.venv`
- Installs all Python packages from `backend\requirements.txt`
- Runs `npm install` in `frontend\`
- Builds the frontend (`npm run build`) into `frontend\dist\`

### Optional Offline AI + Christy Voice Setup (recommended)

1. Install Ollama:

```powershell
winget install Ollama.Ollama
```

2. Pull a local model (fast recommended):

```powershell
ollama pull llama3.2:3b
```

3. Ensure backend deps are installed (includes `pyttsx3` for offline TTS):

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

4. Start AOJ Command OS and verify:
  - `GET http://localhost:8000/api/tts/status` should return `available=true`
  - Christy uses Piper when available (`engine=piper`), else Microsoft Zira fallback (`engine=pyttsx3`)
  - AI will use Ollama when available, and auto-fallback if Ollama is offline

### Piper Voice Setup (Christy)

1. Download Piper for Windows and place `piper.exe` in a folder on your PATH (or use a full executable path).
2. Download a Piper ONNX voice model (example: `en_US-amy-medium.onnx`) and place it under:

```text
backend/assets/piper/
```

3. Set environment variables before starting backend (PowerShell example):

```powershell
$env:PIPER_BIN = "piper"
$env:PIPER_MODEL_PATH = "C:\\path\\to\\AOJ-Server-main\\backend\\assets\\piper\\en_US-amy-medium.onnx"
$env:PIPER_LENGTH_SCALE = "1.08"
# Optional tuning:
# $env:PIPER_SPEAKER_ID = "0"
# $env:PIPER_NOISE_SCALE = "0.667"
# $env:PIPER_NOISE_W = "0.8"
```

4. Start backend and check status:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/tts/status"
```

Expected result when Piper is active:
- `available: true`
- `engine: piper`
- `voice: <model-file-name>.onnx`

### Start the server (single process, recommended)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_production_windows.ps1
```

Open **http://localhost:8000** in your browser.

### Start in development mode (two processes)

```powershell
# Terminal 1 — Backend with auto-reload
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend_windows.ps1

# Terminal 2 — Frontend dev server
powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend_windows.ps1
```

| URL | Purpose |
|---|---|
| http://localhost:5173 | Frontend (dev hot-reload) |
| http://localhost:8000 | Backend API |
| http://localhost:8000/api/health | Health check |
| ws://localhost:8000/ws/live | WebSocket feed |

### Update to a new version

```powershell
git pull
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start_production_windows.ps1
```

---

## Quick Install — Linux / Raspberry Pi

```bash
# Clone
git clone https://github.com/YOUR_ORG/AOJ-Server.git
cd AOJ-Server

# Make scripts executable
chmod +x ./scripts/*.sh

# Install (Pi-specific version includes apt dependencies)
./scripts/install_pi.sh      # Raspberry Pi
# or
./scripts/install_linux.sh   # Generic Linux

# Start production server
./scripts/start_production.sh
```

Open **http://MACHINE_IP:8000** on any device on your LAN.

---

## Manual Development Commands

### Windows — Backend

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Windows — Frontend

```powershell
Set-Location .\frontend
npm.cmd run dev -- --host 0.0.0.0 --port 5173
```

### Linux — Backend

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Linux — Frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## GitHub Actions CI/CD

The repository includes `.github/workflows/ci.yml` which runs automatically on every push.

### What it does

| Job | Trigger | Action |
|---|---|---|
| **Backend** | every push/PR | Installs dependencies, lints with ruff, type-checks with mypy, smoke-tests startup |
| **Frontend** | every push/PR | `npm ci` + `npm run build`, uploads `dist/` as artifact |
| **Windows Installer** | push to `main` or version tag | Runs the full Windows install script, packages a ZIP release |
| **Security Scan** | every push | `pip-audit` + `npm audit` |

### Trigger a manual build

1. Go to your repository on GitHub
2. Click **Actions → AOJ Command OS – CI / Build / Release**
3. Click **Run workflow** → check **Build Windows installer package** → **Run workflow**

### Create a versioned release

Tag your commit to trigger a full release with a downloadable Windows ZIP:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The Actions workflow will:
1. Build and test backend + frontend
2. Package a ZIP containing the full project + built frontend
3. Create a GitHub Release with the ZIP attached and auto-generated release notes

### Setting up Actions on a fork

No secrets are required for the default configuration. The workflow uses `GITHUB_TOKEN` (automatically provided) for creating releases.

---

## AI Assistant

The AI advisor uses a conversational rules engine that:

- **Holds conversation history** — context from previous messages is used to give better answers
- **Suggests games** based on player count, field size, session length, and team handicap
  - *Example: "suggest a game for 20 players on a 5000m² field with a 30% team handicap"*
- **Builds rule sets** — ask it to draft objectives, timers, and scoring for any mode
  - *Example: "build domination rules for 16 players, 25 minutes"*
- **Asks for confirmation** on operational actions (start/stop game, arm/reset device) instead of blocking — reply "yes" or "confirm" to proceed
- **Learns within a session** — tracks topics and actions to improve follow-up answers
- **Integrates custom knowledge** — entries from Admin → Knowledge Base are injected into every response

### Swap in a real LLM

The advisor engine is in `backend/app/ai/advisor.py`. Replace `ask_ai()` with any OpenAI/Anthropic/Ollama call to upgrade from the mock to a real model. The rest of the pipeline (context assembly, safety layer, conversation history) works unchanged.

---

## Project Layout

```text
.github/workflows/    GitHub Actions CI/CD
backend/              FastAPI application
  app/
    ai/               Conversational advisor + context engine
    core/             Safety policy
    models/           SQLAlchemy ORM models
    routes/           API route handlers
    schemas/          Pydantic schemas
    services/         Business logic
frontend/             React + Vite UI
  src/
    components/       Admin panel components
    App.jsx           Main application
firmware/             LoRa field prop firmware (do not modify)
scripts/              Install / launch / package scripts
docs/                 Architecture and field deployment notes
```

---

## Access URLs

| Mode | URL |
|---|---|
| Dev frontend | http://localhost:5173 |
| Dev backend API | http://localhost:8000 |
| Production (single process) | http://MACHINE_IP:8000 |
| Health check | http://MACHINE_IP:8000/api/health |
| WebSocket | ws://MACHINE_IP:8000/ws/live |

## Field Deployment Notes

- Bind to `0.0.0.0` so tablets and phones on the field LAN can connect
- Use a dedicated WiFi hotspot or router — keep the system off internet-facing networks during events
- The database (`backend/aoj.db`) is created automatically on first run
- Back up the database before events using `scripts/backup_database.sh`

