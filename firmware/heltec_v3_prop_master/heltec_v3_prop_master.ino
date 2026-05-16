/*
 * heltec_v3_prop_master.ino
 *
 * Handheld AOJ prop controller for Heltec WiFi LoRa 32 V3.
 *
 * Features:
 * - Uses a rotary encoder (A/B) to select command.
 * - Uses Heltec built-in BOOT button to transmit command.
 * - Optional encoder push button to cycle target device.
 * - Sends AOJ LoRa protocol frames to control props.
 *
 * AOJ frame format:
 *   AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 *
 * Default target is "*" (broadcast to all props).
 *
 * Dependencies:
 *   - RadioLib
 */

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>

// -----------------------------------------------------------------------------
// Board + control pin configuration
// -----------------------------------------------------------------------------

// Heltec WiFi LoRa 32 V3 BOOT button (built-in)
#ifndef PIN_BOOT_BUTTON
#define PIN_BOOT_BUTTON 0
#endif

// Rotary encoder pins (set these to your wiring)
#ifndef PIN_ENCODER_A
#define PIN_ENCODER_A 1
#endif

#ifndef PIN_ENCODER_B
#define PIN_ENCODER_B 2
#endif

// Optional encoder push button (set to -1 if not wired)
#ifndef PIN_ENCODER_SW
#define PIN_ENCODER_SW 3
#endif

// -----------------------------------------------------------------------------
// LoRa settings (match your AOJ network)
// -----------------------------------------------------------------------------

static const float LORA_FREQUENCY_MHZ = 923.0;
static const float LORA_BANDWIDTH_KHZ = 125.0;
static const uint8_t LORA_SPREADING_FACTOR = 9;
static const uint8_t LORA_CODING_RATE = 7;
static const uint8_t LORA_SYNC_WORD = 0x34;
static const int8_t LORA_OUTPUT_POWER_DBM = 17;

// Heltec WiFi LoRa 32 V3 SX1262 pins
static const int PIN_LORA_NSS = 8;
static const int PIN_LORA_DIO1 = 14;
static const int PIN_LORA_RST = 12;
static const int PIN_LORA_BUSY = 13;

static const int PIN_LORA_SCK = 9;
static const int PIN_LORA_MISO = 11;
static const int PIN_LORA_MOSI = 10;

// -----------------------------------------------------------------------------
// AOJ command presets
// -----------------------------------------------------------------------------

struct CommandPreset {
  const char* label;
  const char* command;
  const char* value;
};

static const CommandPreset COMMANDS[] = {
  {"ARM", "ARM", "ALL"},
  {"DISARM", "DISARM", "ALL"},
  {"RESET", "RESET", "ALL"},
  {"STATUS", "STATUS_REQUEST", "NOW"},
  {"ALARM", "TRIGGER_ALARM", "ON"}
};

static const size_t COMMAND_COUNT = sizeof(COMMANDS) / sizeof(COMMANDS[0]);

// Target device IDs. "*" means broadcast to all props.
static const char* TARGETS[] = {
  "*",
  "PROP-ALPHA",
  "BOMB-01",
  "DOM-001",
  "RESP-001"
};

static const size_t TARGET_COUNT = sizeof(TARGETS) / sizeof(TARGETS[0]);

// -----------------------------------------------------------------------------
// Globals
// -----------------------------------------------------------------------------

static SX1262 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);
static volatile bool loraPacketReady = false;

static int commandIndex = 0;
static int targetIndex = 0;

// Encoder + button debouncing
static int lastEncoderA = HIGH;
static uint32_t lastBootChangeMs = 0;
static int lastBootState = HIGH;

static uint32_t lastEncoderSwChangeMs = 0;
static int lastEncoderSwState = HIGH;

static const uint32_t DEBOUNCE_MS = 35;

void IRAM_ATTR onLoraPacketReady() {
  loraPacketReady = true;
}

// -----------------------------------------------------------------------------
// Utility helpers
// -----------------------------------------------------------------------------

String xorCrcHex(const String& payload) {
  uint8_t crc = 0;
  for (size_t i = 0; i < payload.length(); i++) {
    crc ^= static_cast<uint8_t>(payload[i]);
  }

  char out[3];
  snprintf(out, sizeof(out), "%02X", crc);
  return String(out);
}

String generateMessageId() {
  uint32_t v = static_cast<uint32_t>(millis()) ^ static_cast<uint32_t>(esp_random());
  char out[11];
  snprintf(out, sizeof(out), "%010X", v);
  return String(out);
}

String buildFrame(const char* deviceId, const char* command, const char* value, const String& messageId) {
  String payload = "AOJ|" + String(deviceId) + "|" + String(command) + "|" + String(value) + "|" + messageId;
  return payload + "|" + xorCrcHex(payload);
}

void printSelection() {
  Serial.print("[CTRL] Target=");
  Serial.print(TARGETS[targetIndex]);
  Serial.print(" | Command=");
  Serial.print(COMMANDS[commandIndex].label);
  Serial.print(" (");
  Serial.print(COMMANDS[commandIndex].command);
  Serial.print(":");
  Serial.print(COMMANDS[commandIndex].value);
  Serial.println(")");
}

// -----------------------------------------------------------------------------
// Radio setup
// -----------------------------------------------------------------------------

bool setupRadio() {
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);

  int state = radio.begin(
    LORA_FREQUENCY_MHZ,
    LORA_BANDWIDTH_KHZ,
    LORA_SPREADING_FACTOR,
    LORA_CODING_RATE,
    LORA_SYNC_WORD,
    LORA_OUTPUT_POWER_DBM
  );

  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("[LORA] begin failed: ");
    Serial.println(state);
    return false;
  }

  radio.setDio1Action(onLoraPacketReady);

  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("[LORA] startReceive failed: ");
    Serial.println(state);
    return false;
  }

  Serial.println("[LORA] Ready");
  return true;
}

void transmitSelectedCommand() {
  const CommandPreset& selected = COMMANDS[commandIndex];
  const char* target = TARGETS[targetIndex];

  String messageId = generateMessageId();
  String frame = buildFrame(target, selected.command, selected.value, messageId);

  Serial.print("[TX] ");
  Serial.println(frame);

  int txState = radio.transmit(frame);
  int rxState = radio.startReceive();

  if (txState == RADIOLIB_ERR_NONE && rxState == RADIOLIB_ERR_NONE) {
    Serial.println("[TX] OK");
  } else {
    Serial.print("[TX] FAIL tx=");
    Serial.print(txState);
    Serial.print(" rx=");
    Serial.println(rxState);
  }
}

// -----------------------------------------------------------------------------
// Input polling
// -----------------------------------------------------------------------------

void pollEncoderRotation() {
  int a = digitalRead(PIN_ENCODER_A);
  int b = digitalRead(PIN_ENCODER_B);

  if (a != lastEncoderA && a == LOW) {
    if (b == HIGH) {
      commandIndex++;
    } else {
      commandIndex--;
    }

    if (commandIndex < 0) {
      commandIndex = static_cast<int>(COMMAND_COUNT) - 1;
    }
    if (commandIndex >= static_cast<int>(COMMAND_COUNT)) {
      commandIndex = 0;
    }

    printSelection();
  }

  lastEncoderA = a;
}

void pollBootButton() {
  int currentState = digitalRead(PIN_BOOT_BUTTON);
  uint32_t now = millis();

  if (currentState != lastBootState && (now - lastBootChangeMs) > DEBOUNCE_MS) {
    lastBootChangeMs = now;
    lastBootState = currentState;

    // Active-low press on BOOT button
    if (currentState == LOW) {
      transmitSelectedCommand();
    }
  }
}

void pollEncoderSwitch() {
#if PIN_ENCODER_SW >= 0
  int currentState = digitalRead(PIN_ENCODER_SW);
  uint32_t now = millis();

  if (currentState != lastEncoderSwState && (now - lastEncoderSwChangeMs) > DEBOUNCE_MS) {
    lastEncoderSwChangeMs = now;
    lastEncoderSwState = currentState;

    // Active-low press
    if (currentState == LOW) {
      targetIndex++;
      if (targetIndex >= static_cast<int>(TARGET_COUNT)) {
        targetIndex = 0;
      }
      printSelection();
    }
  }
#endif
}

void pollLoraReceive() {
  if (!loraPacketReady) {
    return;
  }

  loraPacketReady = false;

  String frame;
  int state = radio.readData(frame);
  radio.startReceive();

  if (state == RADIOLIB_ERR_NONE) {
    Serial.print("[RX] ");
    Serial.println(frame);
  } else {
    Serial.print("[RX] Read error: ");
    Serial.println(state);
  }
}

// -----------------------------------------------------------------------------
// Arduino entry points
// -----------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);
  pinMode(PIN_ENCODER_A, INPUT_PULLUP);
  pinMode(PIN_ENCODER_B, INPUT_PULLUP);
#if PIN_ENCODER_SW >= 0
  pinMode(PIN_ENCODER_SW, INPUT_PULLUP);
#endif

  Serial.println();
  Serial.println("AOJ Heltec V3 Prop Master");
  Serial.println("Rotate encoder: select command");
  Serial.println("BOOT button: send selected command");
  Serial.println("Encoder push: cycle target device");

  if (!setupRadio()) {
    Serial.println("[FATAL] Radio init failed. Reboot to retry.");
    while (true) {
      delay(1000);
    }
  }

  printSelection();
}

void loop() {
  pollEncoderRotation();
  pollBootButton();
  pollEncoderSwitch();
  pollLoraReceive();
}
