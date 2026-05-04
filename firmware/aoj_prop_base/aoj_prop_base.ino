/**
 * AOJ Command OS — Prop Base Firmware
 * Target: ESP32 with SX1262 LoRa module (e.g. LilyGO T3-S3, Heltec v3, TTGO LoRa32)
 *
 * What this firmware does:
 *  - Registers the prop with the AOJ Command OS server on boot
 *  - Listens for commands: ARM, DISARM, RESET, STATUS_REQUEST, TRIGGER_ALARM
 *  - Sends ACK for every received command
 *  - Broadcasts a STATUS heartbeat every 30 seconds
 *  - Reports battery level and signal strength (RSSI) in status frames
 *
 * Frame format (matches backend LoRa protocol):
 *   AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 *
 * Board library: Heltec ESP32 LoRa v3  OR  RadioLib (https://github.com/jgromes/RadioLib)
 * Required libraries:
 *   - RadioLib  (Install via Arduino Library Manager)
 *
 * Edit the CONFIG section below before flashing.
 */

#include <Arduino.h>
#include <RadioLib.h>

// ─────────────────────────────────────────────
// CONFIG — edit these before flashing
// ─────────────────────────────────────────────

// Unique identifier for this prop — must match the Device ID registered in the
// AOJ Command OS Prop Network module.
#define DEVICE_ID "PROP-ALPHA"

// Prop type label sent in status frames (informational only).
#define PROP_TYPE "Bomb"

// LoRa radio pin assignment — adjust for your board.
// Heltec WiFi LoRa 32 v3 example:
#define LORA_NSS   8
#define LORA_DIO1  14
#define LORA_RST   12
#define LORA_BUSY  13

// LoRa radio parameters — must match the AOJ server radio config.
#define LORA_FREQUENCY   923.0   // MHz — Japan ISM band
#define LORA_BANDWIDTH   125.0   // kHz
#define LORA_SF          9       // Spreading factor
#define LORA_CR          7       // Coding rate (5 = 4/5 … 8 = 4/8)
#define LORA_SYNC_WORD   0x34    // AOJ network sync word

// Heartbeat interval in milliseconds.
#define HEARTBEAT_INTERVAL_MS 30000

// Battery pin (ADC). Set to -1 if not fitted.
// On most ESP32 boards the internal ADC reads 3.3 V full-scale.
#define BATTERY_ADC_PIN 35
#define BATTERY_FULL_MV 4200
#define BATTERY_EMPTY_MV 3300

// ─────────────────────────────────────────────
// Radio object
// ─────────────────────────────────────────────

SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────

enum PropState { STATE_OFFLINE, STATE_ONLINE, STATE_ARMED, STATE_DISARMED, STATE_ALARM };
PropState currentState = STATE_OFFLINE;

volatile bool dataReceived = false;
unsigned long lastHeartbeat = 0;

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/**
 * XOR CRC — matches backend calculate_crc().
 * Computed over all characters in `payload` (the full frame minus the |CRC suffix).
 * Returns a 2-character uppercase hex string.
 */
String calculateCrc(const String &payload) {
  uint8_t crc = 0;
  for (size_t i = 0; i < payload.length(); i++) {
    crc ^= (uint8_t)payload[i];
  }
  char buf[3];
  snprintf(buf, sizeof(buf), "%02X", crc);
  return String(buf);
}

/**
 * Build a complete AOJ frame.
 *  AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 */
String buildFrame(const String &command, const String &value, const String &messageId) {
  String payload = "AOJ|" + String(DEVICE_ID) + "|" + command + "|" + value + "|" + messageId;
  String crc = calculateCrc(payload);
  return payload + "|" + crc;
}

/**
 * Generate a simple 10-character message ID from millis + random.
 */
String generateMessageId() {
  uint32_t val = (uint32_t)millis() ^ (uint32_t)esp_random();
  char buf[11];
  snprintf(buf, sizeof(buf), "%010X", val);
  return String(buf);
}

/**
 * Read battery level as a percentage (0–100).
 * Returns 100 if BATTERY_ADC_PIN is -1.
 */
int readBatteryPercent() {
#if BATTERY_ADC_PIN < 0
  return 100;
#else
  int raw = analogRead(BATTERY_ADC_PIN);
  // ESP32 ADC 12-bit, Vref ~ 3.3 V via voltage divider (adjust multiplier for your circuit).
  int mv = (int)((long)raw * 3300 / 4095) * 2; // assumes 1:1 divider
  int pct = (int)(((long)(mv - BATTERY_EMPTY_MV) * 100) / (BATTERY_FULL_MV - BATTERY_EMPTY_MV));
  return constrain(pct, 0, 100);
#endif
}

const char *stateLabel(PropState s) {
  switch (s) {
    case STATE_ONLINE:    return "online";
    case STATE_ARMED:     return "armed";
    case STATE_DISARMED:  return "disarmed";
    case STATE_ALARM:     return "alarm";
    default:              return "offline";
  }
}

// ─────────────────────────────────────────────
// Radio transmit
// ─────────────────────────────────────────────

void sendFrame(const String &frame) {
  Serial.print("[TX] "); Serial.println(frame);
  int state = radio.transmit(frame);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("[TX] Error: "); Serial.println(state);
  }
  // Return to receive mode after transmit.
  radio.startReceive();
}

// ─────────────────────────────────────────────
// Send ACK back to server
// ─────────────────────────────────────────────

void sendAck(const String &messageId, const String &ackValue = "OK") {
  String frame = buildFrame("ACK", ackValue, messageId);
  sendFrame(frame);
}

// ─────────────────────────────────────────────
// Send status heartbeat
// ─────────────────────────────────────────────

void sendStatus() {
  int battery = readBatteryPercent();
  int rssi    = (int)radio.getRSSI();

  // VALUE encodes: status:battery:rssi:prop_type
  String value = String(stateLabel(currentState)) + ":" +
                 String(battery) + ":" +
                 String(rssi) + ":" +
                 String(PROP_TYPE);

  String mid   = generateMessageId();
  String frame = buildFrame("STATUS", value, mid);
  sendFrame(frame);
}

// ─────────────────────────────────────────────
// Parse and handle incoming frame
// ─────────────────────────────────────────────

void handleFrame(const String &raw) {
  Serial.print("[RX] "); Serial.println(raw);

  // Split by '|'
  String parts[6];
  int partCount = 0;
  int start = 0;
  for (int i = 0; i <= raw.length() && partCount < 6; i++) {
    if (i == (int)raw.length() || raw[i] == '|') {
      parts[partCount++] = raw.substring(start, i);
      start = i + 1;
    }
  }

  if (partCount < 6) { Serial.println("[RX] Malformed frame (too few fields)"); return; }

  const String &header    = parts[0];
  const String &deviceId  = parts[1];
  const String &command   = parts[2];
  const String &value     = parts[3];
  const String &messageId = parts[4];
  const String &rxCrc     = parts[5];

  // Validate header.
  if (header != "AOJ") { Serial.println("[RX] Rejected: bad header"); return; }

  // Validate CRC.
  String payload = header + "|" + deviceId + "|" + command + "|" + value + "|" + messageId;
  if (rxCrc != calculateCrc(payload)) { Serial.println("[RX] Rejected: CRC mismatch"); return; }

  // Only process frames addressed to this prop or broadcast ('*').
  if (deviceId != String(DEVICE_ID) && deviceId != "*") return;

  // Dispatch command.
  if (command == "ARM") {
    currentState = STATE_ARMED;
    Serial.println("[STATE] Armed");
    sendAck(messageId, "OK");
    // TODO: activate your physical indicator (LED, buzzer, relay).
  }
  else if (command == "DISARM") {
    currentState = STATE_DISARMED;
    Serial.println("[STATE] Disarmed");
    sendAck(messageId, "OK");
    // TODO: deactivate physical indicator.
  }
  else if (command == "RESET") {
    currentState = STATE_ONLINE;
    Serial.println("[STATE] Reset to online");
    sendAck(messageId, "OK");
    // TODO: reset countdown timers, LEDs, etc.
  }
  else if (command == "TRIGGER_ALARM") {
    currentState = STATE_ALARM;
    Serial.println("[STATE] Alarm triggered");
    sendAck(messageId, "OK");
    // TODO: sound buzzer, flash LEDs.
  }
  else if (command == "STATUS_REQUEST") {
    sendAck(messageId, "OK");
    sendStatus();
  }
  else {
    // Unknown command — still ACK so server doesn't retry indefinitely.
    Serial.print("[RX] Unknown command: "); Serial.println(command);
    sendAck(messageId, "UNKNOWN");
  }
}

// ─────────────────────────────────────────────
// ISR — flag when a packet arrives
// ─────────────────────────────────────────────

void IRAM_ATTR onReceive() {
  dataReceived = true;
}

// ─────────────────────────────────────────────
// setup()
// ─────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n[AOJ] Prop Base Firmware — " DEVICE_ID);

  // Initialise radio.
  int state = radio.begin(
    LORA_FREQUENCY,
    LORA_BANDWIDTH,
    LORA_SF,
    LORA_CR,
    LORA_SYNC_WORD
  );

  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("[RADIO] Init failed: "); Serial.println(state);
    // Halt — cannot operate without radio.
    while (true) { delay(1000); }
  }

  Serial.println("[RADIO] Initialised OK");

  // Attach interrupt for incoming packets.
  radio.setDio1Action(onReceive);
  radio.startReceive();

  currentState = STATE_ONLINE;

  // Announce presence on boot.
  sendStatus();
  lastHeartbeat = millis();

  Serial.println("[AOJ] Ready");
}

// ─────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────

void loop() {
  // Handle incoming LoRa packet.
  if (dataReceived) {
    dataReceived = false;
    String received;
    int state = radio.readData(received);
    if (state == RADIOLIB_ERR_NONE) {
      handleFrame(received);
    } else {
      Serial.print("[RX] Read error: "); Serial.println(state);
      radio.startReceive();
    }
  }

  // Periodic heartbeat.
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = millis();
    sendStatus();
  }
}
