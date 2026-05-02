# AOJ Command OS Architecture

## Purpose

AOJ Command OS is a local-only field control system for airsoft events. It is designed for a Raspberry Pi deployed at the field, a local router that creates the event LAN, browser clients on tablets or phones, and LoRa-connected props such as bombs, sensors, alarms, and domination points.

The system is intentionally usable without internet access. All operator traffic stays on the event network.

## High-Level Layout

```text
Tablets / Phones / Laptops
          |
          | HTTP + WebSocket
          v
     Field Router / LAN
          |
          v
   Raspberry Pi running:
   - FastAPI backend
   - React frontend build
   - SQLite database
   - LoRa service skeleton
          |
          | LoRa radio link
          v
      Field Props
```

## Main Components

### Backend

Location: `backend/`

Technology:
- FastAPI for the API and WebSocket endpoint
- SQLAlchemy for ORM models and SQLite access
- Uvicorn as the ASGI server

Responsibilities:
- Expose REST endpoints for operations modules
- Maintain live mission state
- Persist field data in SQLite
- Publish live updates to connected clients over WebSocket
- Provide system, AI, and update-center status endpoints

Important backend entry points:
- `app.main:app`
- `/api/health`
- `/ws/live`

### Frontend

Location: `frontend/`

Technology:
- React 18
- Vite 5

Responsibilities:
- Present the tactical dashboard UI
- Provide operator workflows for Mission Control, Schedule, Results Board, Prop Network, System Logs, System Monitor, AI Assistant, and Update Center
- Connect to the backend over HTTP and WebSocket

The frontend is built to static files and can be served locally on the Raspberry Pi.

### Database

Location:
- SQLite file at `backend/aoj_command_os.db`

Responsibilities:
- Store devices, props, missions, schedules, results, logs, and user role definitions
- Keep deployment simple for headless field use

SQLite was chosen because it is easy to back up, deploy, and restore on a single-node Raspberry Pi installation.

### Live Update Layer

WebSocket endpoint:
- `/ws/live`

Responsibilities:
- Notify clients when the system comes online
- Push Mission Control state snapshots
- Broadcast prop command activity
- Support future real-time event propagation from LoRa and monitoring services

### LoRa Service

Location:
- `backend/services/lora_service.py`

Current state:
- Skeleton implementation with queueing, CRC, ACK handling, timeout handling, and mock transport
- Prepared for later SX1262 or similar radio integration

Responsibilities:
- Queue commands to field props
- Track retries and pending acknowledgements
- Maintain basic device status cache

Current limitation:
- The service is mock-first. Real radio transport is not yet wired into hardware drivers.

## Current Backend Modules

### Mission Control

Purpose:
- Create and control the active mission or game session
- Track round state, score changes, and objective status
- Broadcast live state to operators

### Schedule

Purpose:
- Manage the day plan for games, breaks, briefings, and staging windows

### Results Board

Purpose:
- Store completed match results and penalties
- Support after-action review and score summaries

### Prop Network

Purpose:
- Register props
- Send operator commands to props
- Show field-facing status like battery, signal, firmware, and last seen

### System Logs

Purpose:
- Record operational events across mission, prop, AI, Wi-Fi, LoRa, and update categories

### System Monitor

Purpose:
- Report Raspberry Pi or mock host health
- Show CPU, RAM, disk, uptime, database connectivity, LoRa service status, and websocket client count

### AI Assistant

Purpose:
- Provide advisory-only planning help, briefings, summaries, and diagnostics guidance

Current limitation:
- No command execution is allowed through AI
- The service is a local mock advisor, not a live LLM integration

### Update Center

Purpose:
- Report current versions and changelog
- Create SQLite backups
- Reserve future flows for offline update package ingestion, restore, and rollback

Current limitation:
- Upload, restore, and rollback endpoints are placeholders and do not modify runtime files

## Request Flow

### Standard operator request

1. A tablet opens the frontend from the Raspberry Pi over the field LAN.
2. The frontend sends an HTTP request to a FastAPI route.
3. The backend reads or writes SQLite state.
4. If the action affects live state, the backend broadcasts an event on `/ws/live`.
5. Other connected clients update without reloading.

### Prop command flow

1. Operator sends a prop command in the Prop Network module.
2. The backend updates the prop record and logs the action.
3. A websocket event is broadcast to active clients.
4. In the current codebase, LoRa delivery remains a skeleton integration path rather than a completed hardware path.

## Deployment Model

Recommended field model:
- One Raspberry Pi runs the backend, static frontend, database, and support services.
- One router or access point creates the event LAN.
- Operator tablets join that LAN by Wi-Fi.
- LoRa props communicate independently of the Wi-Fi network.

This keeps operator traffic and prop traffic separated by function:
- Wi-Fi is for dashboards and API traffic.
- LoRa is for low-bandwidth prop control and telemetry.

## Design Choices

### Local-first

The platform assumes field conditions with unreliable or unavailable internet. All critical operations work on the local network.

### Safe placeholders for destructive actions

Potentially dangerous update actions such as restore and rollback are intentionally placeholders until a verified offline installer flow exists.

### Mock fallback on non-Pi hosts

System monitoring and LoRa status can operate in a mock mode during development on non-Raspberry Pi systems.

## Planned Growth Areas

- Real LoRa radio integration
- Authenticated users and enforced role-based access control
- Verified offline update packages with signatures
- More detailed device telemetry and field analytics
- Settings module implementation

## Folder Map

- `backend/`: API, models, services, database file
- `frontend/`: React tactical dashboard
- `scripts/`: deployment, startup, and backup scripts
- `docs/`: field and technical documentation
- `firmware/`: future or external microcontroller firmware work