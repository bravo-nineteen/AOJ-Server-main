# Heltec V3 USB LoRa Gateway

This guide adds a USB-serial LoRa gateway path using a Heltec WiFi LoRa 32 V3.

The Raspberry Pi talks to the Heltec over USB serial.
The Heltec talks over LoRa (SX1262) to your field devices.

## Files Added

- firmware/heltec_v3_lora_gateway/heltec_v3_lora_gateway.ino
- src/lora_gateway.py
- examples/lora_gateway_test.py

## Required Hardware

- Raspberry Pi (any model with USB and Python 3)
- Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
- USB-C data cable (Pi to Heltec)
- LoRa antenna attached to Heltec before transmitting

## USB Connection (Pi to Heltec)

1. Connect Heltec V3 to Pi using a USB-C data cable.
2. On Linux, check available serial devices:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

3. Typical device names are `/dev/ttyACM0` or `/dev/ttyUSB0`.

## Arduino IDE / PlatformIO Notes

- Board: ESP32S3 Dev Module (or Heltec V3 profile)
- Upload the firmware:
  - firmware/heltec_v3_lora_gateway/heltec_v3_lora_gateway.ino
- Install library dependency:
  - RadioLib by Jan Gromes

The firmware uses clear constants at the top of the file for:

- frequency
- bandwidth
- spreading factor
- coding rate
- sync word
- output power
- SX1262 pins

Edit those constants to match your region and network.

## Python Dependency

`pyserial` is required.

Install (example):

```bash
pip install pyserial
```

In this repository, `pyserial` is already present in backend requirements.

## Serial Protocol

### Commands from Raspberry Pi to Heltec

- `PING`
  - Response: `PONG`

- `SEND:<message>`
  - Action: transmit `<message>` over LoRa
  - Response: `TX_OK:<message>` or `TX_FAIL:<error_code>`

- `STATUS`
  - Response: `STATUS:READY`

- `RESET_RADIO`
  - Action: reinitialize the SX1262
  - Response: `RADIO_RESET_OK` or `RADIO_RESET_FAIL:<error_code>`

### Async line from Heltec when LoRa packet is received

- `RX:<message>`

### Unknown command

- `ERR:UNKNOWN_COMMAND`

## Python Module Usage

Module path:

- src/lora_gateway.py

Public API:

- `connect(port=None)`
- `send_message(message)`
- `read_messages()`
- `ping()`
- `status()`
- `reset_radio()`

You can use either:

- the `HeltecLoRaGateway` class
- module-level convenience functions

## Example Test Script

Run:

```bash
python examples/lora_gateway_test.py
```

Manual port override:

```bash
python examples/lora_gateway_test.py --port /dev/ttyACM0
```

What it does:

1. Connects to gateway
2. Sends `PING`
3. Requests `STATUS`
4. Sends a test LoRa message
5. Continuously prints incoming `RX:` messages

## Manual Protocol Test (optional)

You can also test directly with a serial terminal at 115200 baud.

Example sequence:

1. `PING`
2. `STATUS`
3. `SEND:HELLO_WORLD`
4. `RESET_RADIO`

## Troubleshooting

### Wrong serial port

- Run `ls /dev/ttyACM* /dev/ttyUSB*` before and after plugging in the Heltec.
- Use manual override in Python: `--port /dev/ttyACM0`.

### No LoRa receive

- Confirm antenna is connected.
- Confirm both radios are on the same frequency, bandwidth, SF, CR, and sync word.
- Confirm remote device is actually transmitting.

### Frequency mismatch

- Check the firmware constants in:
  - firmware/heltec_v3_lora_gateway/heltec_v3_lora_gateway.ino
- Make sure all participating LoRa devices use identical RF settings.

### Heltec not detected

- Try another USB cable (data-capable, not charge-only).
- Try another USB port on the Pi.
- Reflash firmware and reset board.

### Permission denied on Linux serial port

If you get permission errors opening `/dev/ttyACM*` or `/dev/ttyUSB*`:

```bash
sudo usermod -a -G dialout $USER
```

Then log out and log back in (or reboot) before testing again.
