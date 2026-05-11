# LoRa Quick Reference

## Environment Setup

### 1. Raspberry Pi 5 + Waveshare Core1262 (SPI)
```bash
# .env or export
LORA_MODE=rpi_spi
LORA_RPI_SPI_BUS=1
LORA_RPI_SPI_DEVICE=1
LORA_RPI_RST_PIN=17
LORA_RPI_DIO1_PIN=22
LORA_RPI_SPI_SPEED_HZ=8000000
```

**Pre-flight checklist:**
- [ ] SPI enabled: `raspi-config` → Interface → SPI → Yes
- [ ] Module wired: GPIO10/9/11/7 (MOSI/MISO/CLK/CS) + GPIO17/22 (RST/DIO1)
- [ ] User in groups: `groups | grep -E 'gpio|spi'`
- [ ] Python packages: `pip list | grep -E 'RPi|spidev'`

### 2. Windows USB LoRa Module
```powershell
$env:LORA_MODE = "usb_serial"
$env:LORA_USB_PORT = "COM3"        # Find in Device Manager
$env:LORA_USB_BAUDRATE = "9600"
$env:LORA_USB_TIMEOUT = "1.0"
```

**Pre-flight checklist:**
- [ ] Device connected and powered
- [ ] COM port visible in Device Manager
- [ ] Drivers installed (search by device name)
- [ ] Baud rate matches device spec

### 3. Linux USB LoRa Module
```bash
export LORA_MODE=usb_serial
export LORA_USB_PORT=/dev/ttyUSB0
export LORA_USB_BAUDRATE=9600
export LORA_USB_TIMEOUT=1.0
```

**Pre-flight checklist:**
- [ ] Device visible: `lsusb`
- [ ] Port available: `ls -la /dev/ttyUSB*`
- [ ] User in dialout group: `groups | grep dialout`

### 4. Development/Testing
```bash
# Mock mode (no hardware needed)
export LORA_MODE=mock

# Test mode (simulated responses)
export LORA_MODE=test
```

---

## Start Application

**Linux/macOS:**
```bash
cd backend
python app/main.py
```

**Windows:**
```powershell
cd backend
python app\main.py
```

---

## Test Settings API

### Enable Test Mode
```bash
curl -X PUT http://localhost:8000/api/settings/lora_test_mode_enabled \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'
```

### Configure Test Device
```bash
curl -X PUT http://localhost:8000/api/settings/lora_test_device_id \
  -H "Content-Type: application/json" \
  -d '{"value": "DRONE_001"}'
```

### Enable Auto-Response
```bash
curl -X PUT http://localhost:8000/api/settings/lora_test_auto_respond \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'
```

### Inject Errors (Testing Robustness)
```bash
# Enable error injection
curl -X PUT http://localhost:8000/api/settings/lora_test_inject_errors \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'

# Set to fail 30% of messages
curl -X PUT http://localhost:8000/api/settings/lora_test_error_rate \
  -H "Content-Type: application/json" \
  -d '{"value": "30"}'

# Add 500ms latency to responses
curl -X PUT http://localhost:8000/api/settings/lora_test_latency_ms \
  -H "Content-Type: application/json" \
  -d '{"value": "500"}'
```

### Enable Auto-PING
```bash
# Send PING every 10 seconds
curl -X PUT http://localhost:8000/api/settings/lora_test_ping_interval \
  -H "Content-Type: application/json" \
  -d '{"value": "10"}'
```

---

## Diagnostics

### Check System Status
```bash
curl http://localhost:8000/api/lora/diagnostics | jq
```

**Response:**
```json
{
  "mode": "rpi_spi",
  "transport_started": true,
  "pending_ack": 2,
  "tx_count": 1024,
  "rx_count": 987,
  "last_tx_at": 1620000123.456,
  "last_rx_at": 1620000124.789,
  "alive": true,
  "last_error": null
}
```

### List All LoRa Settings
```bash
curl 'http://localhost:8000/api/settings?search=lora' | jq
```

### Get Specific Setting
```bash
curl http://localhost:8000/api/settings/lora_test_mode_enabled
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `SPI device not found` | SPI disabled | `raspi-config` → Interface → SPI → Yes |
| `Permission denied /dev/spidev*` | Wrong group | `sudo usermod -aG spi $USER` (reboot) |
| `USB device not found` | Wrong COM port | Check Device Manager for actual port |
| `Serial timeout` | Wrong baud rate | Verify with device documentation |
| `No response from device` | Wiring issue | Check GPIO connections & power |
| `Module resets constantly` | Voltage drop | Add capacitor near VCC (10-100µF) |

### Enable Debug Logging
```bash
export LORA_DEBUG=1
export LOG_LEVEL=DEBUG
python backend/app/main.py
```

### Manual SPI Test (Raspberry Pi)
```python
import spidev

spi = spidev.SpiDev()
spi.open(1, 1)  # Bus 1, Device 1
spi.max_speed_hz = 8_000_000

# Send test byte
result = spi.xfer2([0xAA])
print(f"Response: {hex(result[0])}")

spi.close()
```

### Manual Serial Test (Windows/Linux)
```python
import serial

# Windows: COM3, Linux: /dev/ttyUSB0
port = serial.Serial('COM3', baudrate=9600, timeout=1.0)
port.write(b"PING\n")
response = port.readline()
print(f"Response: {response}")
port.close()
```

---

## Performance Targets

| Metric | RPi SPI | USB Serial | Mock | Test |
|--------|---------|-----------|------|------|
| Latency | 10-50ms | 5-20ms | <1ms | <1ms |
| Throughput | 1000 msg/min | 2000 msg/min | ∞ | ∞ |
| Typical Range | 10km | 1-5km | N/A | N/A |

---

## Common Commands

### Send PING
```bash
curl -X POST http://localhost:8000/api/lora/send \
  -H "Content-Type: application/json" \
  -d '{"device_id": "DRONE_001", "command": "PING"}'
```

### Get Device Status
```bash
curl http://localhost:8000/api/lora/devices/DRONE_001
```

### Reset LoRa Module
```bash
# On RPi: physically cycle power or
curl -X POST http://localhost:8000/api/lora/reset
```

---

## Documentation

For detailed information, see:
- [LORA_HARDWARE_SETUP.md](LORA_HARDWARE_SETUP.md) - Full hardware guide
- [backend/app/lora/device_drivers.py](backend/app/lora/device_drivers.py) - Implementation
- [backend/app/config.py](backend/app/config.py) - Configuration options

---

**Status**: ✅ Ready | **Version**: 1.0.1
