/*
 * heltec_v3_lora_gateway.ino
 *
 * Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262) USB serial LoRa gateway.
 *
 * Serial protocol (115200 baud):
 *   PING                -> PONG
 *   STATUS              -> STATUS:READY
 *   SEND:<message>      -> TX_OK:<message> or TX_FAIL:<error_code>
 *   RESET_RADIO         -> RADIO_RESET_OK or RADIO_RESET_FAIL:<error_code>
 *   <unknown>           -> ERR:UNKNOWN_COMMAND
 *
 * Async LoRa RX output:
 *   RX:<message>
 *
 * Library dependency:
 *   - RadioLib
 */

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>

// -----------------------------------------------------------------------------
// LoRa / board settings (edit these for your field configuration)
// -----------------------------------------------------------------------------

static const float LORA_FREQUENCY_MHZ = 923.0;
static const float LORA_BANDWIDTH_KHZ = 125.0;
static const uint8_t LORA_SPREADING_FACTOR = 9;
static const uint8_t LORA_CODING_RATE = 7;     // 5..8 => 4/5..4/8
static const uint8_t LORA_SYNC_WORD = 0x34;
static const int8_t LORA_OUTPUT_POWER_DBM = 17;

// Heltec WiFi LoRa 32 V3 (ESP32-S3) SX1262 pins
static const int PIN_LORA_NSS = 8;
static const int PIN_LORA_DIO1 = 14;
static const int PIN_LORA_RST = 12;
static const int PIN_LORA_BUSY = 13;

static const int PIN_LORA_SCK = 9;
static const int PIN_LORA_MISO = 11;
static const int PIN_LORA_MOSI = 10;

// -----------------------------------------------------------------------------
// Globals
// -----------------------------------------------------------------------------

static SX1262 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);

static volatile bool loraPacketReady = false;
static String serialLineBuffer = "";

void IRAM_ATTR onLoraPacketReady() {
  loraPacketReady = true;
}

// -----------------------------------------------------------------------------
// Radio setup/reset
// -----------------------------------------------------------------------------

int setupRadio() {
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
    return state;
  }

  radio.setDio1Action(onLoraPacketReady);

  state = radio.startReceive();
  return state;
}

// -----------------------------------------------------------------------------
// Protocol handlers
// -----------------------------------------------------------------------------

void respondUnknown() {
  Serial.println("ERR:UNKNOWN_COMMAND");
}

void handlePing() {
  Serial.println("PONG");
}

void handleStatus() {
  Serial.println("STATUS:READY");
}

void handleSend(const String &message) {
  if (message.length() == 0) {
    Serial.println("TX_FAIL:EMPTY_MESSAGE");
    return;
  }

  int state = radio.transmit(message);

  // Always return to receive mode after TX.
  int rxState = radio.startReceive();
  if (state == RADIOLIB_ERR_NONE && rxState == RADIOLIB_ERR_NONE) {
    Serial.print("TX_OK:");
    Serial.println(message);
  } else if (state != RADIOLIB_ERR_NONE) {
    Serial.print("TX_FAIL:");
    Serial.println(state);
  } else {
    Serial.print("TX_FAIL:");
    Serial.println(rxState);
  }
}

void handleResetRadio() {
  int state = setupRadio();
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("RADIO_RESET_OK");
  } else {
    Serial.print("RADIO_RESET_FAIL:");
    Serial.println(state);
  }
}

void handleCommand(const String &commandLine) {
  if (commandLine == "PING") {
    handlePing();
    return;
  }

  if (commandLine == "STATUS") {
    handleStatus();
    return;
  }

  if (commandLine == "RESET_RADIO") {
    handleResetRadio();
    return;
  }

  if (commandLine.startsWith("SEND:")) {
    handleSend(commandLine.substring(5));
    return;
  }

  respondUnknown();
}

// -----------------------------------------------------------------------------
// Loop helpers
// -----------------------------------------------------------------------------

void pollSerialCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      if (serialLineBuffer.length() > 0) {
        handleCommand(serialLineBuffer);
        serialLineBuffer = "";
      }
      continue;
    }

    serialLineBuffer += c;

    // Guard against runaway input lines.
    if (serialLineBuffer.length() > 512) {
      serialLineBuffer = "";
      Serial.println("TX_FAIL:LINE_TOO_LONG");
    }
  }
}

void pollLoraReceive() {
  if (!loraPacketReady) {
    return;
  }

  loraPacketReady = false;

  String message;
  int state = radio.readData(message);

  // Keep receiver armed for the next packet.
  radio.startReceive();

  if (state == RADIOLIB_ERR_NONE) {
    Serial.print("RX:");
    Serial.println(message);
  }
}

// -----------------------------------------------------------------------------
// Arduino entry points
// -----------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);

  // Give USB CDC time to enumerate when connected to a Pi.
  delay(300);

  int state = setupRadio();
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("RADIO_RESET_FAIL:");
    Serial.println(state);
    return;
  }

  Serial.println("STATUS:READY");
}

void loop() {
  pollSerialCommands();
  pollLoraReceive();
}
