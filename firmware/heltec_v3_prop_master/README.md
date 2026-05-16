# Heltec V3 Prop Master Firmware

This firmware turns a Heltec WiFi LoRa 32 V3 into a handheld AOJ controller.

## Controls

- Rotate encoder: select command
- Built-in BOOT button: transmit selected command over LoRa
- Encoder push button (optional): cycle target device ID

Default target list starts with `*` (broadcast), so you can control all props.

## File

- `heltec_v3_prop_master.ino`

## Required Library

- RadioLib
- U8g2

## Built-in OLED

The Heltec V3 built-in screen is used as a live status panel.

It displays:

- Current target device ID
- Current selected command
- Last TX status
- Last RX frame/error

## Wiring

LoRa pins are fixed to Heltec V3 SX1262:

- NSS: GPIO8
- DIO1: GPIO14
- RST: GPIO12
- BUSY: GPIO13
- SCK: GPIO9
- MISO: GPIO11
- MOSI: GPIO10

Default input pins:

- Built-in BOOT button: GPIO0 (active low)
- Encoder A: GPIO1
- Encoder B: GPIO2
- Encoder SW: GPIO3 (optional)

You can change any of these at compile time by defining:

- `PIN_BOOT_BUTTON`
- `PIN_ENCODER_A`
- `PIN_ENCODER_B`
- `PIN_ENCODER_SW`

## LoRa Settings

Defaults (must match AOJ network):

- Frequency: 923.0 MHz
- Bandwidth: 125 kHz
- Spreading Factor: 9
- Coding Rate: 7
- Sync Word: 0x34
- TX Power: 17 dBm

## Wire Protocol

Frames are sent as:

`AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC`

Command presets included:

- `ARM`
- `DISARM`
- `RESET`
- `STATUS_REQUEST`
- `TRIGGER_ALARM`

## Typical Use

1. Flash firmware to Heltec V3.
2. Open Serial Monitor at 115200.
3. Rotate encoder to select command.
4. Press BOOT to send command to all props (`*`) or selected target.
5. Watch incoming ACK/status frames in serial output.
