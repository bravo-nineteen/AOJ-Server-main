/*
 * AOJ Prop Base (Dual Transport) - C++ reference firmware
 *
 * Purpose:
 * - Report factual prop telemetry (status, battery, signal strength, firmware)
 * - Support both WiFi (HTTP POST) and LoRa (AOJ frame) reporting
 * - Receive simple LoRa commands and ACK status
 *
 * Backend endpoint expected:
 *   POST /api/props/status-report
 *   {
 *     "device_id": "PROP-001",
 *     "status": "online|armed|disarmed|alarm|maintenance|offline",
 *     "battery_level": 85,
 *     "signal_strength": 77,
 *     "firmware_version": "1.0.0",
 *     "transport": "wifi|lora"
 *   }
 *
 * NOTE:
 * - This is a portable base template. You must adapt radio pins/driver for your board.
 * - Uses Arduino style APIs for practical ESP32 usage.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// Optional: enable if you have RadioLib installed and a supported LoRa board.
// #include <RadioLib.h>

// ------------------------------------------------------------
// CONFIG
// ------------------------------------------------------------

static const char* DEVICE_ID = "PROP-001";
static const char* FIRMWARE_VERSION = "1.0.0";
static const char* PROP_AUTH_TOKEN = "REPLACE_WITH_ISSUED_PROP_TOKEN";

static const char* WIFI_SSID = "YOUR_WIFI_SSID";
static const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
static const char* SERVER_BASE_URL = "http://192.168.1.50:8000"; // AOJ backend

static const uint32_t STATUS_INTERVAL_MS = 15000;
static const uint32_t WIFI_RETRY_MS = 5000;

// ADC battery pin (board specific)
static const int BATTERY_ADC_PIN = 35;

// LoRa placeholders (board specific)
// SX1262 radio = new Module(NSS_PIN, DIO1_PIN, RESET_PIN, BUSY_PIN);

// ------------------------------------------------------------
// STATE
// ------------------------------------------------------------

enum PropStatus {
  STATUS_OFFLINE,
  STATUS_ONLINE,
  STATUS_ARMED,
  STATUS_DISARMED,
  STATUS_ALARM,
  STATUS_MAINTENANCE
};

PropStatus g_status = STATUS_ONLINE;
unsigned long g_lastStatusReport = 0;
unsigned long g_lastWifiTry = 0;

// ------------------------------------------------------------
// HELPERS
// ------------------------------------------------------------

const char* statusToString(PropStatus s) {
  switch (s) {
    case STATUS_ARMED: return "armed";
    case STATUS_DISARMED: return "disarmed";
    case STATUS_ALARM: return "alarm";
    case STATUS_MAINTENANCE: return "maintenance";
    case STATUS_OFFLINE: return "offline";
    default: return "online";
  }
}

int readBatteryPercent() {
  int raw = analogRead(BATTERY_ADC_PIN);
  // Basic conversion placeholder (tune for your board/divider)
  int mv = (int)((raw / 4095.0f) * 3300.0f * 2.0f);
  int pct = (int)(((mv - 3300) / 900.0f) * 100.0f);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

int readSignalStrengthWifi() {
  if (WiFi.status() != WL_CONNECTED) {
    return 0;
  }
  long rssi = WiFi.RSSI(); // typically -30 to -90 dBm
  int normalized = (int)map((int)rssi, -100, -40, 0, 100);
  if (normalized < 0) normalized = 0;
  if (normalized > 100) normalized = 100;
  return normalized;
}

// XOR CRC for AOJ LoRa frame consistency
String calculateCrc(const String& payload) {
  uint8_t crc = 0;
  for (size_t i = 0; i < payload.length(); i++) {
    crc ^= (uint8_t)payload[i];
  }
  char buf[3];
  snprintf(buf, sizeof(buf), "%02X", crc);
  return String(buf);
}

String buildAojFrame(const String& command, const String& value, const String& messageId) {
  String core = "AOJ|" + String(DEVICE_ID) + "|" + command + "|" + value + "|" + messageId;
  return core + "|" + calculateCrc(core);
}

String randomMessageId() {
  char buf[11];
  snprintf(buf, sizeof(buf), "%010X", (uint32_t)(esp_random() ^ millis()));
  return String(buf);
}

bool postStatusReport(const char* transport, int battery, int signal) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  HTTPClient http;
  String url = String(SERVER_BASE_URL) + "/api/props/status-report";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Prop-Token", PROP_AUTH_TOKEN);

  String body = "{";
  body += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  body += "\"status\":\"" + String(statusToString(g_status)) + "\",";
  body += "\"battery_level\":" + String(battery) + ",";
  body += "\"signal_strength\":" + String(signal) + ",";
  body += "\"firmware_version\":\"" + String(FIRMWARE_VERSION) + "\",";
  body += "\"transport\":\"" + String(transport) + "\"";
  body += "}";

  int code = http.POST(body);
  http.end();
  return code >= 200 && code < 300;
}

void ensureWifiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  if (millis() - g_lastWifiTry < WIFI_RETRY_MS) {
    return;
  }
  g_lastWifiTry = millis();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

// ------------------------------------------------------------
// LoRa command handling (placeholder skeleton)
// ------------------------------------------------------------

void handleLoraCommand(const String& rawFrame) {
  // Expected: AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
  // Parse, validate CRC, apply command, then ACK.

  // Example command behavior:
  // ARM -> g_status = STATUS_ARMED
  // DISARM -> g_status = STATUS_DISARMED
  // RESET -> g_status = STATUS_ONLINE
  // TRIGGER_ALARM -> g_status = STATUS_ALARM
  // STATUS_REQUEST -> force status send

  // TODO: Implement parser with your radio driver receive loop.
  (void)rawFrame;
}

void sendLoraStatusFrame(int battery, int signal) {
  String value = String(statusToString(g_status)) + ":" + String(battery) + ":" + String(signal);
  String frame = buildAojFrame("STATUS", value, randomMessageId());

  // TODO: Send frame with your LoRa driver.
  // radio.transmit(frame);
  Serial.print("[LORA TX] ");
  Serial.println(frame);
}

// ------------------------------------------------------------
// Arduino lifecycle
// ------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(250);

  // If your board requires ADC setup, place it here.
  analogReadResolution(12);

  ensureWifiConnected();

  // TODO: Initialize LoRa radio here (frequency/SF/BW/sync-word).
  // int state = radio.begin(923.0, 125.0, 9, 7, 0x34);

  g_lastStatusReport = 0;
}

void loop() {
  ensureWifiConnected();

  // TODO: Poll LoRa receive and call handleLoraCommand(raw).

  unsigned long now = millis();
  if (now - g_lastStatusReport >= STATUS_INTERVAL_MS) {
    g_lastStatusReport = now;

    int battery = readBatteryPercent();
    int wifiSignal = readSignalStrengthWifi();

    // 1) Prefer WiFi status report if connected.
    bool posted = postStatusReport("wifi", battery, wifiSignal);

    // 2) Always emit LoRa status frame as backup transport.
    sendLoraStatusFrame(battery, wifiSignal);

    if (!posted) {
      // Optional: could queue retry or store local pending status.
      Serial.println("[WARN] WiFi status report failed; LoRa fallback sent.");
    }
  }

  delay(20);
}
