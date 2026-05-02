# AOJ Command OS

AOJ Command OS is a headless Raspberry Pi field command system for airsoft events.
It is designed to run on a local network without internet dependency, with operators connecting through browser clients on tablets, phones, or laptops.

## Core Architecture

- Backend: Python FastAPI
- Frontend: React + Vite
- Database: SQLite
- Live updates: WebSockets
- Network model: local network only
- Hardware target: Raspberry Pi (headless)
- UX style: tactical OS command interface

## Folder Structure

```
backend/
frontend/
firmware/
scripts/
docs/
```

## Run Locally

### 1) Start Backend (FastAPI)

From the `backend` directory:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend health check:

```text
http://localhost:8000/api/health
```

### 2) Start Frontend (React + Vite)

From the `frontend` directory:

```bash
npm install
npm run dev
```

Open in browser:

```text
http://localhost:5173
```

## Raspberry Pi Deployment Notes

- Run backend and frontend services bound to `0.0.0.0` to expose them on LAN.
- Use the Raspberry Pi local IP address when connecting from other devices.
- Keep the deployment isolated on event LAN for operational safety.

## Current Starter Features

- FastAPI API scaffold with `/api/health` endpoint
- WebSocket endpoint at `/ws/live`
- React tactical dashboard with live socket status and event feed panel
