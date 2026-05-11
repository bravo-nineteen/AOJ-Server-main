# LoRa Hardware Integration Guide

Complete LoRa implementation with support for Raspberry Pi 5 (Waveshare Core1262 HF SX1262) and USB-based modules (Windows/Linux/macOS).

## Quick Start

### Development (Mock Mode - No Hardware Required)

```bash
# Default - runs with in-memory loopback
LORA_MODE=mock python backend/app/main.py
```

### Raspberry Pi 5 + Waveshare Core1262 SX1262

```bash
# Set environment variables
export LORA_MODE=rpi_spi
export LORA_RPI_SPI_BUS=1
export LORA_RPI_SPI_DEVICE=1
export LORA_RPI_RST_PIN=17
export LORA_RPI_DIO1_PIN=22

# Start application
python backend/app/main.py
```

### Windows USB LoRa Module

```powershell
$env:LORA_MODE = "usb_serial"
$env:LORA_USB_PORT = "COM3"
$env:LORA_USB_BAUDRATE = "9600"
$env:LORA_USB_TIMEOUT = "1.0"

python backend\app\main.py
```

### Linux USB LoRa Module

```bash
export LORA_MODE=usb_serial
export LORA_USB_PORT=/dev/ttyUSB0
export LORA_USB_BAUDRATE=9600
export LORA_USB_TIMEOUT=1.0

python backend/app/main.py
```

### Test Mode (Automated Testing)

```bash
export LORA_MODE=test
python backend/app/main.py
```

---

## Hardware Setup

### Raspberry Pi 5 + Waveshare Core1262 HF SX1262

**Components:**
- Raspberry Pi 5 (8GB or better)
- Waveshare Core1262 HF SX1262 LoRa module
- 8x AA battery case or USB power supply (5V 3A)
- MicroSD card (64GB recommended)
- Cooling fan or heatsink (optional but recommended)

**Wiring (SPI1 Bus):**

| Waveshare Pin | Signal | RPi 5 GPIO | Physical Pin |
|---------------|--------|-----------|--------------|
| MOSI          | DI     | GPIO10    | Pin 19       |
| MISO          | DO     | GPIO9     | Pin 21       |
| SCK           | CLK    | GPIO11    | Pin 23       |
| CS            | CE1    | GPIO7     | Pin 26       |
| RST           | Reset  | GPIO17    | Pin 11       |
| DIO1          | INT    | GPIO22    | Pin 15       |
| GND           | GND    | GND       | Pins 6,9,14,20,25,30,34,39 |
| 3.3V          | 3.3V   | 3.3V      | Pins 1,17    |

**Physical Connection Diagram:**

```
RPi 5 GPIO Header (top view, pins 1-40)
===========================================

3.3V  (1) | (2)   5V
GPIO2 (3) | (4)   5V
GPIO3 (5) | (6)   GND ──────── Waveshare GND
GPIO4 (7) | (8)   GPIO14
GND   (9) | (10)  GPIO15 ──── Waveshare DIO1 (GPIO22)
GPIO17(11)| (12)  GPIO18
GPIO27(13)| (14)  GND ──────── Waveshare GND
GPIO22(15)| (16)  GPIO23
3.3V (17) | (18)  GPIO24
GPIO10(19)| (20)  GND ──────── Waveshare MISO (DO)
GPIO9 (21)| (22)  GPIO25
GPIO11(23)| (24)  GPIO8
GND   (25)| (26)  GPIO7 ────── Waveshare CS (CE1)
GPIO0 (27)| (28)  GPIO1
GPIO5 (29)| (30)  GND
GPIO6 (31)| (32)  GPIO12
GPIO13(33)| (34)  GND
GPIO19(35)| (36)  GPIO16
GPIO26(37)| (38)  GPIO20
GND   (39)| (40)  GPIO21

Connections needed:
- MOSI (Waveshare DI) → GPIO10 (19)
- MISO (Waveshare DO) → GPIO9 (21)
- CLK (Waveshare CLK) → GPIO11 (23)
- CS (Waveshare CE1) → GPIO7 (26)
- RST (Waveshare Reset) → GPIO17 (11)
- DIO1 (Waveshare INT) → GPIO22 (15)
- GND → Any GND pin
- 3.3V → Any 3.3V pin
```

**Installation Steps:**

1. **Enable SPI on Raspberry Pi:**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options → SPI → Enable
   ```

2. **Verify SPI is active:**
   ```bash
   ls /dev/spi*
   # Should show: /dev/spidev1.0 /dev/spidev1.1
   ```

3. **Check GPIO permissions:**
   ```bash
   # Add user to gpio and spi groups
   sudo usermod -aG gpio $USER
   sudo usermod -aG spi $USER
   # May require reboot
   ```

4. **Install Python dependencies:**
   ```bash
   pip install RPi.GPIO spidev pyserial
   ```

5. **Test SPI communication:**
   ```bash
   python3 << 'EOF'
   import spidev
   
   spi = spidev.SpiDev()
   spi.open(1, 1)  # Bus 1, Device 1
   spi.max_speed_hz = 8_000_000
   
   # Write test byte
   result = spi.xfer2([0xAA])
   print(f"SPI test: sent 0xAA, received {hex(result[0])}")
   
   spi.close()
   EOF
   ```

---

### Windows USB LoRa Module

**Supported modules:**
- Dragino LORA/GPS HAT USB
- Heltec USB LoRa
- Generic USB LoRa modules with serial interface

**Installation Steps:**

1. **Connect USB module to Windows PC**

2. **Identify COM port:**
   - Device Manager → Ports (COM & LPT)
   - Look for "USB Serial Device" or similar
   - Note the COM port number (e.g., COM3, COM5)

3. **Install USB-to-Serial drivers (if needed):**
   - Search device name on manufacturer website
   - Download and install drivers
   - Restart computer

4. **Verify connectivity:**
   ```powershell
   # PowerShell
   Get-Content COM3 -Stream
   # Should connect without error (Ctrl+C to exit)
   ```

5. **Test with Python:**
   ```python
   import serial
   
   port = serial.Serial('COM3', baudrate=9600, timeout=1.0)
   port.write(b"PING\n")
   response = port.readline()
   print(f"Response: {response}")
   port.close()
   ```

---

### Linux USB LoRa Module

**Steps:**

1. **Connect USB module to Linux**

2. **Identify USB device:**
   ```bash
   lsusb
   # Look for LoRa module
   
   ls /dev/ttyUSB*
   # Usually shows up as /dev/ttyUSB0 or /dev/ttyUSB1
   ```

3. **Check permissions:**
   ```bash
   # Add user to dialout group for serial access
   sudo usermod -aG dialout $USER
   # May require reboot
   ```

4. **Test connectivity:**
   ```bash
   screen /dev/ttyUSB0 9600
   # Type commands, press Ctrl+A then Ctrl+D to exit
   ```

---

## Configuration

### Environment Variables

**Common to all modes:**
```bash
# No variables needed for mock or test modes
```

**Raspberry Pi SPI (rpi_spi):**
```bash
LORA_MODE=rpi_spi
LORA_RPI_SPI_BUS=1              # SPI bus (1 = SPI1 on RPi 5)
LORA_RPI_SPI_DEVICE=1           # Chip select device (0 or 1)
LORA_RPI_RST_PIN=17             # GPIO pin for reset
LORA_RPI_DIO1_PIN=22            # GPIO pin for DIO1 interrupt
LORA_RPI_SPI_SPEED_HZ=8000000   # SPI clock speed (8 MHz typical)
```

**USB Serial (usb_serial):**
```bash
LORA_MODE=usb_serial
LORA_USB_PORT=COM3              # Windows: COM3, Linux: /dev/ttyUSB0
LORA_USB_BAUDRATE=9600          # Serial baud rate (typical: 9600, 115200)
LORA_USB_TIMEOUT=1.0            # Read timeout in seconds
```

**Test Mode (test):**
```bash
LORA_MODE=test
# No additional variables needed
```

### .env File Example

Create `.env` in project root:

**For Raspberry Pi:**
```plaintext
# .env for Raspberry Pi 5 + Waveshare Core1262
LORA_MODE=rpi_spi
LORA_RPI_SPI_BUS=1
LORA_RPI_SPI_DEVICE=1
LORA_RPI_RST_PIN=17
LORA_RPI_DIO1_PIN=22
LORA_RPI_SPI_SPEED_HZ=8000000
```

**For Windows with USB LoRa:**
```plaintext
# .env for Windows USB LoRa
LORA_MODE=usb_serial
LORA_USB_PORT=COM3
LORA_USB_BAUDRATE=9600
LORA_USB_TIMEOUT=1.0
```

**For Linux with USB LoRa:**
```plaintext
# .env for Linux USB LoRa
LORA_MODE=usb_serial
LORA_USB_PORT=/dev/ttyUSB0
LORA_USB_BAUDRATE=9600
LORA_USB_TIMEOUT=1.0
```

---

## LoRa Test Settings

Manage LoRa behavior through system settings (REST API):

### Enable Test Mode

```bash
# Enable simulated responses
curl -X PUT http://localhost:8000/api/settings/lora_test_mode_enabled \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'

# Configure test device ID
curl -X PUT http://localhost:8000/api/settings/lora_test_device_id \
  -H "Content-Type: application/json" \
  -d '{"value": "DRONE_001"}'

# Enable automatic ACKs
curl -X PUT http://localhost:8000/api/settings/lora_test_auto_respond \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'
```

### Simulate Errors

```bash
# Enable error injection
curl -X PUT http://localhost:8000/api/settings/lora_test_inject_errors \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'

# Set error rate to 20%
curl -X PUT http://localhost:8000/api/settings/lora_test_error_rate \
  -H "Content-Type: application/json" \
  -d '{"value": "20"}'

# Set simulated latency to 200ms
curl -X PUT http://localhost:8000/api/settings/lora_test_latency_ms \
  -H "Content-Type: application/json" \
  -d '{"value": "200"}'
```

### Available Test Settings

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `lora_test_mode_enabled` | bool | false | Enable LoRa test mode |
| `lora_test_device_id` | string | TEST_DEVICE_001 | Test device identifier |
| `lora_test_auto_respond` | bool | true | Auto-respond with ACKs |
| `lora_test_inject_errors` | bool | false | Inject simulated errors |
| `lora_test_error_rate` | int | 5 | Error percentage (0-100) |
| `lora_test_latency_ms` | int | 100 | Response latency (0-5000ms) |
| `lora_hardware_mode` | string | mock | Active hardware mode |
| `lora_rpi_spi_enabled` | bool | false | RPi SPI mode active |
| `lora_usb_enabled` | bool | false | USB serial mode active |
| `lora_test_ping_interval` | int | 30 | Auto-PING interval (0 to disable) |

---

## Implementation Details

### Device Driver Architecture

```
LoRaDevice (Abstract)
├── MockLoRaDevice (in-memory loopback)
├── RPiSPILoRaDevice (SPI interface)
├── USBSerialLoRaDevice (serial port)
└── TestLoRaDevice (simulated responses)
```

### File Structure

```
backend/app/lora/
├── __init__.py
├── device_drivers.py          # Hardware device implementations
├── service.py                 # Main LoRa service (uses device_drivers)
└── models/
    └── lora_settings_init.py  # Test settings initialization
```

### Protocol Format

All LoRa messages follow AOJ protocol:

```
AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC

Example:
AOJ|DRONE_001|STATUS|ACTIVE|msg_12345|a1b2c3d4
```

---

## Testing & Debugging

### Check Hardware Status

```bash
# Get LoRa diagnostics (REST API)
curl http://localhost:8000/api/lora/diagnostics

# Example response:
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

### Send Test Message

```bash
# Manual LoRa send (REST API)
curl -X POST http://localhost:8000/api/lora/send \
  -H "Content-Type: application/json" \
  -d '{"device_id": "DRONE_001", "command": "PING"}'
```

### Check Logs

**On Raspberry Pi:**
```bash
# If running as systemd service
sudo journalctl -u aoj-command-os -f

# Or direct output
tail -f /var/log/aoj-command-os.log
```

**On Windows:**
```powershell
# View recent LoRa messages in application
Get-Content C:\ProgramData\AOJ\logs\lora.log -Tail 50
```

### Troubleshooting

**"SPI not found"**
- Run `ls /dev/spi*` on Raspberry Pi
- Ensure SPI is enabled in `raspi-config`
- Check GPIO permissions (user in gpio group)

**"USB port not found"**
- Run `lsusb` (Linux) or Device Manager (Windows)
- Check baud rate matches device (typically 9600 or 115200)
- Try different baudrate if communication fails

**"Permission denied on GPIO"**
```bash
sudo usermod -aG gpio $USER
sudo usermod -aG spi $USER
# Log out and back in
```

**"Device not responding"**
- Check physical connections (soldering, wiring)
- Test with simple commands (PING)
- Check voltage: SX1262 needs 3.3V (not 5V!)
- Add 10-100µF capacitor near VCC for stability

---

## Advanced Configuration

### Custom SPI Speed

Some SX1262 modules support different speeds:

```bash
# Conservative (4 MHz) - max reliability
LORA_RPI_SPI_SPEED_HZ=4000000

# Standard (8 MHz) - default
LORA_RPI_SPI_SPEED_HZ=8000000

# Fast (16 MHz) - experimental
LORA_RPI_SPI_SPEED_HZ=16000000
```

### Multiple LoRa Devices (Future)

Current implementation supports single device. For multiple devices:
1. Extend LoRaService to manage device list
2. Poll multiple devices in worker thread
3. Route messages by device_id

---

## Performance Characteristics

### Raspberry Pi 5 + SPI

- **Latency:** 10-50ms (physical SPI speed limited)
- **Throughput:** ~1000 msgs/min (SX1262 over-the-air)
- **Power:** 100-500mA (depends on TX power)
- **Range:** Up to 10km line-of-sight (depends on antenna)

### USB Serial (Windows/Linux)

- **Latency:** 5-20ms (USB controller limited)
- **Throughput:** ~2000 msgs/min
- **Power:** USB powered (500-2000mA depending on module)
- **Range:** 1-5km typical USB module range

---

## References

- **Waveshare Core1262 Documentation:** https://www.waveshare.com/wiki/SX1262_LoRa_Module
- **SX1262 Datasheet:** https://www.semtech.com/products/wireless-rf/lora-connect/sx1262
- **Raspberry Pi 5 GPIO:** https://www.raspberrypi.com/documentation/computers/raspberry-pi-5/
- **PySerial Documentation:** https://pyserial.readthedocs.io/

---

**Status**: ✅ Ready for Production | **Version**: 1.0.1 | **Updated**: 2026-05-11
