# Quick Start Guide for AOJ Command OS

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **Docker & Docker Compose** (optional, for containerized deployment)

## Local Development Setup

### 1. Clone and Setup Backend

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp backend/.env.example ../.env.example
# Edit with your configuration
```

### 2. Setup Frontend

```bash
cd frontend
npm install
```

### 3. Start Backend (Development)

```bash
cd backend
# With watch/reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# With environment from .env
source ../.env  # (or .env.bat on Windows)
uvicorn app.main:app --host $HOST --port $PORT --reload
```

### 4. Start Frontend (Development)

```bash
cd frontend
npm run dev
# Frontend will be available at http://localhost:5173
```

### 5. Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/api/health

## Docker Deployment

### Single Container Deployment

```bash
docker-compose up -d

# View logs
docker-compose logs -f aoj-app

# Check status
docker-compose ps

# Stop
docker-compose down
```

### Build Locally

```bash
docker build -t aoj-command-os:latest .
docker run -p 8000:8000 \
  -e LORA_MODE=mock \
  -e LOG_LEVEL=INFO \
  aoj-command-os:latest
```

### With Ollama LLM Support

```bash
# Uncomment ollama service in docker-compose.yml
docker-compose up -d

# Pull a model (inside container or ollama host)
ollama pull llama3.2:3b

# Enable in .env:
# OLLAMA_ENABLED=true
# OLLAMA_HOST=http://ollama:11434
```

## Configuration

### Environment Variables (`.env`)

Create a `.env` file in the project root. See `.env.example` for all options:

```bash
# API
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# LoRa Hardware Mode
LORA_MODE=mock  # Options: mock, rpi_spi, usb_serial, test

# AI/LLM
OLLAMA_ENABLED=false
OLLAMA_MODEL=llama3.2:3b

# TTS Engine
TTS_ENGINE=pyttsx3  # Options: piper, pyttsx3

# Authentication
AUTH_ENABLED=false
```

## Database

### Initialize Database

The backend automatically initializes the SQLite database on first start:

```bash
cd backend
python -c "from app.database import init_db; init_db(); print('✓ Database initialized')"
```

### Backup Database

```bash
# Manual backup
bash scripts/backup_database.sh

# Check backups
ls -la backend/backups/
```

### Run Migrations

```bash
cd backend
alembic upgrade head
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Build Frontend

```bash
cd frontend
npm run build
```

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
PORT=9000 uvicorn app.main:app --reload
```

### Database Locked

```bash
# Remove stale locks
rm -f backend/aoj_command_os.db-shm
rm -f backend/aoj_command_os.db-wal
```

### Python Module Not Found

```bash
# Ensure you're in virtual environment
source backend/.venv/bin/activate

# Reinstall dependencies
pip install -r backend/requirements.txt
```

### WebSocket Connection Issues

```bash
# Verify Uvicorn is running with WebSocket support
# Check for "Uvicorn running on http://..." message
# Ensure backend is accessible from frontend's URL
```

## Common Tasks

### View API Documentation

```bash
# Start backend, then visit:
http://localhost:8000/docs
```

### Enable Debug Logging

```bash
# In .env:
LOG_LEVEL=DEBUG

# Or as environment variable:
export LOG_LEVEL=DEBUG
```

### Check System Health

```bash
curl http://localhost:8000/api/health | jq .
```

### View Application Logs

```bash
# Docker logs
docker-compose logs -f --tail=50 aoj-app

# File logs (if configured)
tail -f backend/logs/*.log
```

## Performance Tips

- Use `--workers 4` in production: `uvicorn app.main:app --workers 4`
- Enable caching for static assets
- Use WebSocket for live updates instead of polling
- Database indices on frequently queried columns

## Next Steps

1. **Configure LoRa Hardware** — Update `LORA_MODE` and hardware pins in `.env`
2. **Enable Ollama** — Set `OLLAMA_ENABLED=true` and start ollama container
3. **Add Game Modes** — Use Settings UI to create custom game modes
4. **Build Field Network** — Register props and test LoRa connectivity
5. **Review API Docs** — Visit `/docs` to explore all endpoints

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Endpoints](docs/API_ENDPOINTS.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [LoRa Protocol](docs/LORA_PROTOCOL.md)
- [Deployment Guide](docs/DEPLOYMENT_PI.md)
- [Improvements Implemented](IMPROVEMENTS_IMPLEMENTED.md)
