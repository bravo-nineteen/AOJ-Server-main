# AOJ Command OS Deployment on Raspberry Pi

## Goal

This guide describes a practical Raspberry Pi deployment for an airsoft field command station running:
- FastAPI backend
- built React frontend
- SQLite database
- local Ollama LLM (offline)
- local operator access over Wi-Fi LAN

## Recommended Hardware

- Raspberry Pi 4 or newer
- Reliable power supply
- High-quality microSD card or SSD
- Local router or access point
- Optional UPS or battery backup for admin table deployment
- Optional LoRa radio module for future hardware integration

## Software Assumptions

- Raspberry Pi OS Lite or similar headless Linux image
- SSH enabled for remote administration
- Python 3 installed
- Node.js and npm available through apt packages

## Project Layout

Relevant deployment areas:
- `backend/`
- `frontend/`
- `scripts/`
- `docs/`

## Deployment Strategy

AOJ Command OS is designed as a single-node appliance deployment.

Recommended model:
- The Raspberry Pi runs the backend and serves the built frontend locally.
- Tablets connect to the Pi over the field router.
- The SQLite database remains local on the Pi.

## Installation Script

Use:
- `scripts/install_pi.sh`
- `scripts/setup_pi_ollama.sh`

What it does:
- updates apt metadata
- installs Python and Node dependencies from apt
- creates a backend virtual environment in `backend/.venv`
- installs backend requirements from `backend/requirements.txt`
- runs `npm install` in `frontend/`
- builds the frontend static bundle in `frontend/dist`

What it does not do:
- it does not enable systemd services automatically
- it does not overwrite system configuration files beyond package installation

Additional Ollama setup (`scripts/setup_pi_ollama.sh`):
- installs Ollama runtime
- enables `ollama` systemd service
- pulls default model `qwen2.5:0.5b` (override with `OLLAMA_MODEL=...`)

## Service Startup Scripts

### Backend

Use:
- `scripts/start_backend.sh`

Behavior:
- changes into `backend/`
- starts `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Frontend

Use:
- `scripts/start_frontend.sh`

Behavior:
- serves `frontend/dist` using `python3 -m http.server`
- binds to `0.0.0.0`
- defaults to port `4173`

You can override the frontend port with:
- `AOJ_FRONTEND_PORT`

## Systemd Service Templates

Use:
- `scripts/create_services.sh`

Behavior:
- generates template service files into `scripts/systemd/`
- does not copy files into `/etc/systemd/system`
- does not call `systemctl enable`

This is deliberate. Review service units before installing them on a live field box.

Environment variables supported by the generator:
- `AOJ_USER`
- `AOJ_GROUP`

Default assumptions:
- user `pi`
- group `pi`

## Example Deployment Procedure

1. Copy the repository to the Raspberry Pi.
2. SSH into the Pi.
3. Run `chmod +x scripts/*.sh` if execute bits were not preserved.
4. Run `./scripts/install_pi.sh`.
5. Run `./scripts/setup_pi_ollama.sh`.
5. Test backend with `./scripts/start_backend.sh`.
6. In a second terminal, test frontend with `./scripts/start_frontend.sh`.
7. Open the frontend from a tablet using the Pi IP and port `4173`.
8. If the tests pass, generate service templates with `./scripts/create_services.sh`.
9. Review the generated unit files.
10. Copy them into `/etc/systemd/system` manually and enable them only after review.

## Validation Checklist

After installation:
- Open `http://PI_IP:8000/api/health`
- Open `http://PI_IP:4173`
- Confirm the frontend can reach the backend
- Confirm websocket live updates connect
- Verify database file exists at `backend/data/aoj_command_os.db`
- Verify Ollama is reachable at `http://127.0.0.1:11434/api/tags`

## Database Backups

Use:
- `scripts/backup_database.sh`

Behavior:
- copies `backend/aoj_command_os.db`
- stores timestamped backups in `backend/backups/`
- does not delete old backups

Operational guidance:
- make a backup before event day
- make another backup after major schedule or result entry changes
- keep one copy off the Pi if possible

## Runtime URLs

Typical field URLs:
- Frontend: `http://PI_IP:4173`
- Backend API: `http://PI_IP:8000`
- Health check: `http://PI_IP:8000/api/health`
- WebSocket: `ws://PI_IP:8000/ws/live`

## AI Provider On Pi 5

AOJ now supports Ollama-only mode on Raspberry Pi 5.

Recommended backend runtime environment:
- `OLLAMA_BASE=http://127.0.0.1:11434`
- `OLLAMA_STRICT=true`

With `OLLAMA_STRICT=true`, AOJ will not fall back to mock/rules-engine responses when Ollama is unavailable.

## Service Management Example

After manual installation of reviewed service files:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aoj-backend.service
sudo systemctl enable --now aoj-frontend.service
sudo systemctl status aoj-backend.service
sudo systemctl status aoj-frontend.service
```

## Operational Recommendations for Field Use

- Keep the Pi and router in a protected marshal or admin zone
- Use stable power and avoid USB power sources of unknown quality
- Label the Pi IP address on the admin kit
- Keep one keyboard or SSH-capable laptop available for emergency maintenance
- Test the complete stack before players arrive

## Current Limitations

- Update install, restore, and rollback flows are placeholders only
- LoRa hardware transport is not yet fully integrated
- There is no completed authentication layer yet

## Suggested Future Improvements

- Replace the Python static server with nginx or Caddy for a longer-lived appliance deployment
- Add a reverse proxy so frontend and backend share a single origin
- Add automated health-check restart policy monitoring
- Add signed offline update packages for event-safe upgrades