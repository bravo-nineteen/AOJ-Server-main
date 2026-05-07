# AOJ Command OS — ESP32 Field Props

C++ Arduino sketches for all field props. Each prop connects to the AOJ backend via **LoRa** (primary) and optionally **WiFi** (supplementary status reporting).

---

## Folder structure

```
firmware/props/
├── AOJ_Core/               ← Shared library — install once
│   ├── AOJ_Core.h          ← Umbrella include
│   ├── AOJ_BoardConfig.h   ← Pin defs: Heltec V2 / V3 / generic ESP32
│   ├── AOJ_Comms.h         ← Frame build/parse, CRC, message IDs, battery ADC
│   ├── AOJ_LoRa.h          ← RadioLib wrapper (SX1262 / SX1276)
│   ├── AOJ_WiFi.h          ← Optional HTTP status reporting
│   └── library.properties
│
├── prop_bomb/
│   └── prop_bomb.ino       ← Countdown bomb, defuse button
│
├── prop_bomb_heltec_v2_keypad/
│   └── prop_bomb_heltec_v2_keypad.ino
│                          ← Keypad + LCD + web-config bomb for Heltec V2
│
├── domination_point/
│   └── domination_point.ino ← Capture-and-hold point
│
├── respawn_station/
│   └── respawn_station.ino  ← Player respawn button station
│
├── CP_Unit/
│   └── CP_Unit.ino      ← Dual-unit ready/countdown respawn station for Heltec V3
│
└── GM_Unit/
   └── GM_Unit.ino      ← Heltec V3 game horn/siren unit (LoRa + dedicated WiFi remote)
```

---

## Supported boards

| Board | Radio | Select with |
|---|---|---|
| Heltec WiFi LoRa 32 **V2** | SX1276 | `#define BOARD_HELTEC_V2` |
| Heltec WiFi LoRa 32 **V3** | SX1262 | `#define BOARD_HELTEC_V3` *(default)* |
| TTGO LoRa32 / generic ESP32 | SX1276 | `#define BOARD_ESP32_GENERIC` |

Uncomment the correct line near the top of each `.ino`. Pin numbers can be overridden individually by `#define`-ing them before including `AOJ_Core.h`.

---

## Required Arduino libraries

Install via **Arduino IDE → Library Manager**:

| Library | Use |
|---|---|
| **RadioLib** | LoRa radio driver (SX1262 + SX1276) |
| **Adafruit NeoPixel** | Optional — only if `NEOPIXEL_COUNT > 0` |

Board support package: **Heltec ESP32** or **esp32 by Espressif** (≥ 2.0).

---

## Installing AOJ_Core

The `AOJ_Core/` folder must be visible to the Arduino IDE as a library.

**Option A — symlink (recommended on Linux/Mac):**
```bash
ln -s /path/to/firmware/props/AOJ_Core ~/Arduino/libraries/AOJ_Core
```

**Option B — copy:**
Copy the entire `AOJ_Core/` folder into `~/Arduino/libraries/` (Windows: `Documents\Arduino\libraries\`).

**Option C — sketch-local include:**
Copy `AOJ_Core/` next to the `.ino` folder and change the includes to relative paths:
```cpp
#include "../AOJ_Core/AOJ_Core.h"
```

---

## Quick-start per prop

### 1. Register the device in AOJ Prop Network

In the AOJ web UI → **Prop Network** → Add Prop.  
Set the `Device ID` to match `#define DEVICE_ID` in the sketch.  
Optionally set an auth token and copy it to `#define PROP_TOKEN`.

### 2. Edit the config block at the top of the `.ino`

```cpp
#define BOARD_HELTEC_V3          // your board
#define DEVICE_ID   "BOMB-01"    // must match server record
#define WIFI_SSID   "FieldNet"   // leave USE_WIFI 0 to skip
#define SERVER_URL  "http://192.168.1.100:8000"
```

### 3. Flash and verify serial output

At 115200 baud you should see:
```
[AOJ] Bomb prop — BOMB-01
[LORA] Ready
[AOJ] Ready
```

---

## LoRa configuration

Default RF settings match the AOJ server defaults (923 MHz, SF9, BW125, sync word 0x34).  
Override before flashing if your regional band differs:
```cpp
#define LORA_FREQUENCY   915.0   // North America
#define LORA_SF          10
```

---

## Prop reference

### prop_bomb

| # | Detail |
|---|---|
| Commands | `ARM [VALUE=seconds]`, `DISARM`, `RESET`, `SET_TIMER`, `STATUS_REQUEST` |
| Events | `EXPLODED`, `DEFUSED`, `STATUS` |
| Defuse | Hold `DEFUSE_BTN` for `DEFUSE_HOLD_MS` (default 3 s) |
| Timer | Default 5 min — server can override with `ARM VALUE=180` |

### prop_bomb_heltec_v2_keypad

| # | Detail |
|---|---|
| Target | Heltec WiFi LoRa 32 V2 (SX1276) |
| Features | 4x3 keypad arming/defuse, 16x2 I2C LCD, EEPROM config, AP web config |
| Server Commands | `ARM`, `DISARM`, `RESET`, `SET_TIMER`, `STATUS_REQUEST`, `TRIGGER_ALARM` |
| Events | `STATUS`, `ARMED`, `DEFUSED`, `EXPLODED` |
| Note | Uses Heltec-safe GPIO remap so LoRa remains stable |

### domination_point

| # | Detail |
|---|---|
| Commands | `ARM`, `DISARM`, `RESET`, `SET_TEAM VALUE=RED\|BLUE\|NEUTRAL`, `STATUS_REQUEST` |
| Events | `CAPTURED VALUE=RED\|BLUE`, `CONTESTED`, `STATUS` |
| Capture | Hold team button for `CAP_TIME_MS` (default 10 s) uncontested |
| Two buttons | `BTN_RED_PIN` / `BTN_BLUE_PIN` — set `BTN_BLUE_PIN -1` for single-button mode |

### respawn_station

| # | Detail |
|---|---|
| Commands | `ENABLE`, `DISABLE`, `RESET`, `SET_TEAM VALUE=RED\|BLUE\|ALL`, `SET_RESPAWN_COUNT VALUE=n`, `STATUS_REQUEST` |
| Events | `RESPAWN VALUE=TEAM:remaining`, `STATUS` |
| Cooldown | `RESPAWN_COOLDOWN_MS` (default 5 s) between spawns at this station |
| Count limit | `SET_RESPAWN_COUNT 10` — station disables automatically when exhausted |

### CP_Unit

| # | Detail |
|---|---|
| Target | Heltec WiFi LoRa 32 V3 with SSD1309 OLED, READY button, ACTION button, buzzer |
| Server LoRa | AOJ-compatible `STATUS`, `RESPAWN`, `GAMEOVER`, and `ACK` frames using `DEVICE_ID` |
| Peer LoRa | Uses `AOJCP|...` packets for ready sync, countdown, count sync, and settings sync between the two field units |
| Commands | `STATUS_REQUEST`, `RESET`, `ENABLE`/`ARM`, `DISABLE`/`DISARM`, `TRIGGER_ALARM`, plus optional `SET_MODE`, `SET_LIMIT`, `SET_COUNTDOWN`, `SET_RESPAWN_DELAY`, `SET_TEAM` |
| Modes | Record-only, kill limit, limited respawns, flag capture |
| Portal | Hold READY during boot to open AP config page at `http://192.168.4.1` |

### GM_Unit

| # | Detail |
|---|---|
| Target | Heltec WiFi LoRa 32 V3 with buzzer + relay-controlled horn |
| Primary Triggers | `GAME_START` and `GAME_END` run 10-second buzzer countdown then 3-second horn pulse |
| Alarm Trigger | `TRIGGER_ALARM`, `BOMB_EXPLODED`, `EXPLODED`, or `ALARM` runs immediate 3-second horn pulse |
| Utility Commands | `STATUS_REQUEST`, `TEST`, `SIREN_TEST` |
| WiFi Remote | Dedicated SSID/pass/token settings and HTTP endpoints for remote trigger/testing |

## PC Simulation Tests

Run both CP_Unit and GM_Unit logic simulations on desktop:

```bash
python firmware/props/run_pc_prop_tests.py
```

Individual harnesses:

```bash
python firmware/props/CP_Unit/test_harness.py
python firmware/props/GM_Unit/test_harness.py
```

---

## Adding a new prop

1. Copy an existing sketch folder (e.g. `prop_bomb/`) and rename it.
2. Change `DEVICE_ID`, `PROP_TYPE`, and `FW_VERSION`.
3. Adjust hardware pin `#define`s.
4. Implement your state machine in `loop()` following the same pattern:
   - Poll `lora.available()` → `aojParseFrame()` → dispatch.
   - Build and send events with `aojBuildFrame()` + `lora.send()`.
   - Send `ACK` for every command received.
   - Call `sendStatus()` on the heartbeat timer.

---

## WiFi status reporting

Set `#define USE_WIFI 1` to enable.  
The prop will POST to `POST /api/props/status-report` on the backend after each heartbeat.  
LoRa remains the primary channel — WiFi is best-effort and silently skipped if the network is unavailable.

Token: generate one in **AOJ Admin → Prop Network → rotate token** and paste it into `PROP_TOKEN`.
