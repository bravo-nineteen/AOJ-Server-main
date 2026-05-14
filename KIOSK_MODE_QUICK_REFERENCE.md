# AOJ Command OS - Kiosk Mode Quick Reference

## System Status

Check if system is running:
```bash
sudo systemctl status aoj-production aoj-kiosk
```

## Common Operations

### View Real-Time Logs
```bash
# Backend server logs
sudo journalctl -u aoj-production -f

# Browser display logs
sudo journalctl -u aoj-kiosk -f

# All AOJ logs
sudo journalctl -g AOJ -f
```

### Restart System
```bash
# Restart backend only
sudo systemctl restart aoj-production

# Restart browser only
sudo systemctl restart aoj-kiosk

# Restart everything
sudo systemctl restart aoj-production aoj-kiosk
```

### Emergency Access (If Stuck in Kiosk)
```bash
# Option 1: SSH from another machine
ssh pi@raspberrypi.local
sudo systemctl stop aoj-kiosk

# Option 2: Local terminal (Alt+Ctrl+F2)
# Login as: pi
# Then run: sudo systemctl stop aoj-kiosk
```

### Access System on Network

From any device on the same network:
- **Command UI:** http://raspberrypi.local:8000
- **API Docs:** http://raspberrypi.local:8000/docs
- **LoRa Props:** http://raspberrypi.local:8000/api/props
- **System Health:** http://raspberrypi.local:8000/api/health

Or use IP directly:
- Replace `raspberrypi.local` with your Pi's IP (e.g., `192.168.1.50`)

### Enable/Disable Kiosk Mode

**Enable (start on boot):**
```bash
sudo systemctl enable aoj-kiosk.service
```

**Disable (don't launch browser on boot):**
```bash
sudo systemctl disable aoj-kiosk.service
sudo reboot
```

### Reboot System
```bash
sudo reboot
```

System will automatically restart AOJ services.

### Shutdown System
```bash
sudo shutdown -h now
```

### Check System Resources
```bash
# CPU and memory usage
top -bn1 | head -20

# Storage space
df -h

# Temperature (Pi only)
vcgencmd measure_temp

# Network connectivity
ping 8.8.8.8
```

## Troubleshooting

### Browser shows blank/loading screen
- Wait 15-20 seconds for backend to initialize
- Check backend health: `curl http://localhost:8000/api/health`
- View logs: `sudo journalctl -u aoj-production -n 50`

### Backend won't start
```bash
# Check for port conflicts
sudo lsof -i :8000

# Try starting manually
./scripts/start_production.sh

# Check for missing dependencies
./scripts/install_pi.sh
```

### LoRa hardware not found
```bash
# Enable SPI: sudo raspi-config → Interface Options → SPI → Enable
# Verify: ls -la /dev/spidev*
```

### System crashes or restarts
```bash
# Check systemd journal for crash reason
sudo journalctl -xe

# Check disk space (low disk can cause crashes)
df -h
```

### Cannot SSH to device
- Ensure SSH service is enabled: `sudo systemctl enable ssh`
- Find IP: `hostname -I` (or check router DHCP clients)
- Try: `ssh pi@<IP_ADDRESS>`

## Performance Tips

### Improve Responsiveness
```bash
# Reduce workers if running on low-spec Pi
sudo systemctl edit aoj-production
# Add: Environment="WORKERS=1"
```

### Optimize Storage
```bash
# Clear old logs
sudo journalctl --vacuum=time=7d

# Clear package cache
sudo apt-get autoclean
sudo apt-get autoremove
```

### Monitor Temperature
```bash
# For Raspberry Pi
watch -n 1 'vcgencmd measure_temp'

# Pi should stay below 80°C under normal load
```

## Advanced Features

### Remote Access via SSH Tunneling
```bash
# From your laptop
ssh -L 8000:localhost:8000 pi@raspberrypi.local
# Then visit: http://localhost:8000
```

### Access Database Directly
```bash
# SQLite database location
~/AOJ-Server/backend/data/aoj.db

# Use sqlite3 to browse
sqlite3 ~/AOJ-Server/backend/data/aoj.db ".tables"
```

### View Backend Configuration
```bash
# Check environment variables used by service
sudo systemctl cat aoj-production

# Check active environment
ps aux | grep uvicorn
```

## System Maintenance

### Weekly
- Check disk space: `df -h`
- Review logs for errors: `sudo journalctl -p 3 -xn 50`

### Monthly
- Clear old journal logs: `sudo journalctl --vacuum=time=30d`
- Update system: `sudo apt-get update && sudo apt-get upgrade`

### Quarterly
- Backup database: `cp ~/AOJ-Server/backend/data/aoj.db ~/backup/`
- Check SD card health: `dmesg | grep -i mmc`
- Review LoRa signal quality logs

### Annually
- Archive old logs and data
- Clean up old firmware backups
- Update all dependencies: `pip install --upgrade -r backend/requirements.txt`

## Contact & Support

- **Documentation:** See [KIOSK_MODE_SETUP.md](KIOSK_MODE_SETUP.md)
- **API Reference:** http://raspberrypi.local:8000/docs
- **System Logs:** `sudo journalctl -u aoj-production -u aoj-kiosk`
- **Issues:** Check GitHub issues or contact admin

---

**Last Updated:** May 2026
