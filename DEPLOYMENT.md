# Production Deployment Guide for AOJ Command OS

## Overview

This guide provides best practices and step-by-step instructions for deploying AOJ Command OS to production environments (Raspberry Pi, Windows, Linux servers).

## Pre-Deployment Checklist

### Infrastructure
- [ ] Target device specs noted (RAM, storage, CPU)
- [ ] Network connectivity verified (WiFi/Ethernet stability tested)
- [ ] Backup strategy in place (automated backups configured)
- [ ] Power backup considered (UPS for field operations)

### Security
- [ ] SSL/TLS certificates obtained (if using reverse proxy)
- [ ] API authentication enabled in `.env` (AUTH_ENABLED=true)
- [ ] Firewall rules configured (only needed ports open)
- [ ] Database backups encrypted
- [ ] Credentials not committed to git

### Performance
- [ ] Database indexed for production queries
- [ ] Uvicorn workers configured (4-8 recommended)
- [ ] Frontend build optimized (`npm run build`)
- [ ] WebSocket connection pooling tested
- [ ] Load testing completed (50+ concurrent connections)

## Deployment Methods

### Method 1: Docker (Recommended)

#### Prerequisites
- Docker and Docker Compose installed
- 2GB RAM minimum
- 5GB storage (SQLite + LoRa assets + backups)

#### Steps

1. **Prepare Environment**
   ```bash
   # Create production .env
   cp .env.example .env
   
   # Edit for production
   nano .env
   # Set: DEPLOYMENT_MODE=production
   # Set: LOG_LEVEL=INFO
   # Set: LORA_MODE=usb_serial (or appropriate hardware)
   ```

2. **Build and Deploy**
   ```bash
   # Build production image
   docker build -t aoj-prod:$(date +%Y%m%d) .
   
   # Run container
   docker run -d \
     --name aoj-command-os \
     --restart unless-stopped \
     -p 8000:8000 \
     --env-file .env \
     -v aoj-data:/app/backend \
     aoj-prod:$(date +%Y%m%d)
   ```

3. **Verify Deployment**
   ```bash
   # Check container status
   docker ps | grep aoj
   
   # View logs
   docker logs -f aoj-command-os
   
   # Health check
   curl http://localhost:8000/api/health
   ```

4. **Setup Auto-Restart**
   ```bash
   # Container restarts automatically with `--restart unless-stopped`
   # System-level startup script (systemd):
   sudo nano /etc/systemd/system/aoj-docker.service
   
   # [Unit]
   # Description=AOJ Command OS Docker Container
   # After=docker.service
   # Requires=docker.service
   #
   # [Service]
   # Type=simple
   # Restart=unless-stopped
   # ExecStart=/usr/bin/docker start aoj-command-os
   # ExecStop=/usr/bin/docker stop aoj-command-os
   #
   # [Install]
   # WantedBy=multi-user.target
   
   sudo systemctl daemon-reload
   sudo systemctl enable aoj-docker.service
   ```

### Method 2: Native Installation (Raspberry Pi / Linux)

#### Prerequisites
- Python 3.11+
- Node.js 18+
- ~1GB RAM
- ~3GB storage

#### Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourepo/AOJ-Server.git
   cd AOJ-Server
   ```

2. **Setup Backend**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate  # or .venv/Scripts/activate on Windows
   pip install -r requirements.txt
   pip install gunicorn  # Production WSGI server
   ```

3. **Setup Frontend**
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

4. **Create systemd Service** (Linux)
   ```bash
   sudo nano /etc/systemd/system/aoj-backend.service
   
   # [Unit]
   # Description=AOJ Command OS Backend
   # After=network.target
   #
   # [Service]
   # Type=notify
   # User=aoj
   # WorkingDirectory=/home/aoj/AOJ-Server/backend
   # Environment="PATH=/home/aoj/AOJ-Server/backend/.venv/bin"
   # ExecStart=/home/aoj/AOJ-Server/backend/.venv/bin/gunicorn \
   #   -w 4 \
   #   -b 0.0.0.0:8000 \
   #   -k uvicorn.workers.UvicornWorker \
   #   app.main:app
   # Restart=always
   # RestartSec=10
   #
   # [Install]
   # WantedBy=multi-user.target
   
   sudo systemctl daemon-reload
   sudo systemctl enable aoj-backend.service
   sudo systemctl start aoj-backend.service
   ```

5. **Setup Reverse Proxy** (nginx)
   ```bash
   sudo nano /etc/nginx/sites-available/aoj
   
   # upstream aoj_backend {
   #     server 127.0.0.1:8000;
   # }
   #
   # server {
   #     listen 80;
   #     server_name aoj.yourfield.local;
   #     client_max_body_size 100M;
   #
   #     location / {
   #         proxy_pass http://aoj_backend;
   #         proxy_set_header Host $host;
   #         proxy_set_header X-Real-IP $remote_addr;
   #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   #     }
   #
   #     location /ws/live {
   #         proxy_pass http://aoj_backend;
   #         proxy_http_version 1.1;
   #         proxy_set_header Upgrade $http_upgrade;
   #         proxy_set_header Connection "Upgrade";
   #     }
   # }
   
   sudo ln -s /etc/nginx/sites-available/aoj /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Method 3: Windows Native

Using PowerShell install scripts provided in `scripts/`:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
.\scripts\install_windows.ps1

# Start services
.\scripts\start_production.ps1
```

This creates Task Scheduler jobs and starts both backend and frontend.

## Hardware-Specific Configuration

### Raspberry Pi 5

```bash
# In .env:
LORA_MODE=rpi_spi
LORA_RPI_SPI_BUS=1
LORA_RPI_SPI_DEVICE=1
LORA_RPI_RST_PIN=17
LORA_RPI_DIO1_PIN=22

# Grant GPIO access
sudo usermod -a -G gpio $USER
```

### USB LoRa Dongle (Windows/Linux/macOS)

```bash
# In .env:
LORA_MODE=usb_serial
LORA_USB_PORT=/dev/ttyUSB0  # Linux
# OR
LORA_USB_PORT=COM3  # Windows

# Verify port
ls /dev/ttyUSB*  # Linux
Get-SerialPort  # PowerShell
```

## Monitoring & Maintenance

### System Monitoring

```bash
# Check resource usage
docker stats aoj-command-os

# Or on native install
top
df -h
free -h
```

### Log Monitoring

```bash
# Docker logs
docker logs -f --tail=50 aoj-command-os

# With filtering
docker logs aoj-command-os | grep "ERROR\|WARN"

# System journal (Linux)
journalctl -u aoj-backend.service -f
```

### Automated Backups

```bash
# Add to crontab
crontab -e

# 2 AM daily backup
0 2 * * * /path/to/AOJ-Server/scripts/backup_database.sh

# Verify backups
ls -la /path/to/AOJ-Server/backend/backups/
```

## Troubleshooting

### High Memory Usage
```bash
# Restart to clear memory leaks
docker restart aoj-command-os

# Or check for connection leaks
netstat -an | grep -c ESTABLISHED
```

### WebSocket Connection Drops
```bash
# Check firewall rules
sudo iptables -L -n

# Monitor disconnections in logs
docker logs aoj-command-os | grep "WebSocket\|disconnect"
```

### Database Corruption
```bash
# Restore from backup
cp backend/backups/aoj_command_os.db.backup backend/aoj_command_os.db

# Verify integrity
sqlite3 backend/aoj_command_os.db "PRAGMA integrity_check;"
```

### LoRa Not Reachable
```bash
# Check device connectivity
docker exec aoj-command-os curl http://localhost:8000/api/health

# Restart LoRa service
docker restart aoj-command-os  # Restarts everything, or:
# curl -X POST http://localhost:8000/api/lora/restart (if endpoint exists)
```

## Performance Tuning

### Uvicorn Workers (Production)
```bash
# In docker-compose.yml or startup script:
# Workers = 2 * (CPU cores) + 1
# For 4-core system: 9 workers

uvicorn app.main:app --workers 9 --worker-class uvicorn.workers.UvicornWorker
```

### Database Connection Pool
```bash
# In .env:
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### WebSocket Heartbeat
Already configured in code:
- Heartbeat interval: 30 seconds
- Auto-reconnect on stale detection
- Configurable in `core/websocket.py`

## Update Procedure

### Minor Updates (Patches)

```bash
# Docker
docker pull aoj-prod:latest
docker-compose up -d  # Pulls and restarts

# Native
git pull
pip install -r backend/requirements.txt --upgrade
npm install (from frontend/)
systemctl restart aoj-backend
```

### Major Updates (Breaking Changes)

```bash
# 1. Backup everything
bash backend/scripts/backup_database.sh

# 2. Review breaking changes (check CHANGELOG.md)

# 3. Run migrations
alembic upgrade head

# 4. Test in staging first

# 5. Deploy to production
```

## Disaster Recovery

### Recovery from Database Corruption
```bash
if sqlite3 aoj_command_os.db "PRAGMA integrity_check;" | grep -q "error"; then
  cp aoj_command_os.db aoj_command_os.db.corrupted
  cp backups/aoj_command_os.db.latest aoj_command_os.db
fi
```

### Full System Restore
```bash
# From encrypted backup
gpg --decrypt aoj_backup_encrypted.gpg > aoj_backup.tar.gz
tar -xzf aoj_backup.tar.gz
# Restore files to original locations
```

## Security Hardening

### Enable API Authentication
```bash
# In .env:
AUTH_ENABLED=true
API_KEYS=prod-key-1:admin,prod-key-2:operator

# In requests:
curl -H "X-API-Key: prod-key-1" http://localhost:8000/api/...
```

### Enable HTTPS (with reverse proxy)
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ... rest of config
}
```

### Firewall Rules (Ubuntu/Debian)
```bash
sudo ufw allow 8000/tcp  # Backend API
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (if using nginx)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Documentation Links

- [Architecture](docs/ARCHITECTURE.md)
- [LoRa Hardware Setup](docs/LORA_HARDWARE_SETUP.md)
- [API Endpoints](docs/API_ENDPOINTS.md)
- [Quick Start](QUICK_START.md)

---

**Last Updated:** May 12, 2026
