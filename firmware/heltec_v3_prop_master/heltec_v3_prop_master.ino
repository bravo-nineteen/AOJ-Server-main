/*
 * heltec_v3_prop_master_fixed.ino
 *
 * Handheld AOJ prop controller for Heltec WiFi LoRa 32 V3.
 *
 * Features:
 * - Uses a rotary encoder A/B to select command.
 * - Uses Heltec built-in BOOT button to transmit command.
 * - Optional encoder push button cycles target device.
 * - Sends AOJ LoRa protocol frames to control props.
 *
 * AOJ frame format:
 *   AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 *
 * Confirmed working OLED setup for this Heltec V3:
 * - OLED SDA: GPIO17
 * - OLED SCL: GPIO18
 * - OLED RST: GPIO21
 * - VEXT: GPIO36
 * - VEXT active LOW
 * - OLED driver: SSD1306
 *
 * Dependencies:
 * - RadioLib
 * - U8g2
 */

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <RadioLib.h>
#include <U8g2lib.h>

// -----------------------------------------------------------------------------
// Board + control pin configuration
// -----------------------------------------------------------------------------

#ifndef PIN_BOOT_BUTTON
#define PIN_BOOT_BUTTON 0
#endif

// Rotary encoder pins
#ifndef PIN_ENCODER_A
#define PIN_ENCODER_A 1
#endif

#ifndef PIN_ENCODER_B
#define PIN_ENCODER_B 2
#endif

// Optional encoder push button
// Set to -1 if not wired
#ifndef PIN_ENCODER_SW
#define PIN_ENCODER_SW 3
#endif

// -----------------------------------------------------------------------------
// LoRa settings
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
// Heltec V3 built-in OLED wiring
// -----------------------------------------------------------------------------

static const int PIN_OLED_SDA = 17;
static const int PIN_OLED_SCL = 18;
static const int PIN_OLED_RST = 21;

// Correct for your board.
// The previous code used GPIO35. That caused dim dots / corrupt OLED.
static const int PIN_VEXT = 36;

// Heltec V3 VEXT is active LOW.
#ifndef VEXT_ACTIVE_HIGH
#define VEXT_ACTIVE_HIGH 0
#endif

// Keep SSD1306 because your first OLED test worked.
#ifndef AOJ_OLED_DRIVER
#define AOJ_OLED_DRIVER 1
#endif

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

// Target device IDs.
// "*" means broadcast to all props.
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

#if AOJ_OLED_DRIVER == 2
static U8G2_SH1106_128X64_NONAME_F_HW_I2C display(
  U8G2_R0,
  PIN_OLED_RST,
  PIN_OLED_SCL,
  PIN_OLED_SDA
);
#else
static U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(
  U8G2_R0,
  PIN_OLED_RST,
  PIN_OLED_SCL,
  PIN_OLED_SDA
);
#endif

static int commandIndex = 0;
static int targetIndex = 0;

static bool displayReady = false;
static String lastTxStatus = "IDLE";
static String lastRxStatus = "-";

static int lastEncoderA = HIGH;

static uint32_t lastBootChangeMs = 0;
static int lastBootState = HIGH;

static uint32_t lastEncoderSwChangeMs = 0;
static int lastEncoderSwState = HIGH;

static const uint32_t DEBOUNCE_MS = 35;

// -----------------------------------------------------------------------------
// Interrupts
// -----------------------------------------------------------------------------

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

String clampText(const String& text, size_t maxLen) {
  if (text.length() <= maxLen) {
    return text;
  }

  return text.substring(0, maxLen);
}

void drawSafeString(int x, int y, const String& text, size_t maxLen) {
  String safe = clampText(text, maxLen);
  display.drawStr(x, y, safe.c_str());
}

// -----------------------------------------------------------------------------
// Display
// -----------------------------------------------------------------------------

void refreshDisplay() {
  if (!displayReady) {
    return;
  }

  display.clearBuffer();
  display.setFont(u8g2_font_6x12_tf);

  display.drawStr(0, 10, "AOJ PROP MASTER");
  display.drawHLine(0, 13, 128);

  drawSafeString(0, 26, "TGT: " + String(TARGETS[targetIndex]), 20);
  drawSafeString(0, 38, "CMD: " + String(COMMANDS[commandIndex].label), 20);
  drawSafeString(0, 50, "TX : " + lastTxStatus, 20);
  drawSafeString(0, 62, "RX : " + lastRxStatus, 20);

  display.sendBuffer();
}

void initDisplay() {
  pinMode(PIN_VEXT, OUTPUT);

#if VEXT_ACTIVE_HIGH
  digitalWrite(PIN_VEXT, HIGH);
#else
  digitalWrite(PIN_VEXT, LOW);
#endif

  delay(300);

  pinMode(PIN_OLED_RST, OUTPUT);
  digitalWrite(PIN_OLED_RST, LOW);
  delay(100);
  digitalWrite(PIN_OLED_RST, HIGH);
  delay(300);

  Wire.end();
  delay(20);

  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
  Wire.setClock(100000);

  bool ok = display.begin();

  if (ok) {
    displayReady = true;
    display.setBusClock(100000);
    display.setContrast(255);
    display.clearBuffer();

    display.setFont(u8g2_font_6x12_tf);
    display.drawStr(0, 12, "AOJ PROP MASTER");
    display.drawStr(0, 30, "OLED OK");
    display.drawStr(0, 48, "Starting...");
    display.sendBuffer();

    delay(700);
    refreshDisplay();
  } else {
    displayReady = false;
    Serial.println("[OLED] Init failed");
  }
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

  refreshDisplay();
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
    Serial.print("[LORA] Begin failed: ");
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

  lastTxStatus = "SENDING";
  refreshDisplay();

  int txState = radio.transmit(frame);
  int rxState = radio.startReceive();

  if (txState == RADIOLIB_ERR_NONE && rxState == RADIOLIB_ERR_NONE) {
    Serial.println("[TX] OK");
    lastTxStatus = "OK " + String(selected.label);
  } else {
    Serial.print("[TX] FAIL tx=");
    Serial.print(txState);
    Serial.print(" rx=");
    Serial.println(rxState);

    lastTxStatus = "FAIL " + String(txState);
  }

  refreshDisplay();
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
    lastRxStatus = clampText(frame, 18);
  } else {
    Serial.print("[RX] Read error: ");
    Serial.println(state);
    lastRxStatus = "ERR " + String(state);
  }

  refreshDisplay();
}

// -----------------------------------------------------------------------------
// Arduino entry points
// -----------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("AOJ Heltec V3 Prop Master");
  Serial.println("OLED: SDA17 SCL18 RST21 VEXT36 LOW");

  initDisplay();

  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);
  pinMode(PIN_ENCODER_A, INPUT_PULLUP);
  pinMode(PIN_ENCODER_B, INPUT_PULLUP);

#if PIN_ENCODER_SW >= 0
  pinMode(PIN_ENCODER_SW, INPUT_PULLUP);
#endif

  Serial.println("Rotate encoder: select command");
  Serial.println("BOOT button: send selected command");
  Serial.println("Encoder push: cycle target device");

  if (!setupRadio()) {
    Serial.println("[FATAL] Radio init failed.");

    lastTxStatus = "LORA FAIL";
    refreshDisplay();

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