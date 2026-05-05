/**
 * AOJ_WiFi.h
 * ─────────────────────────────────────────────────────────────────────────────
 * Optional WiFi + HTTP status-reporting for AOJ props.
 *
 * WiFi is SUPPLEMENTARY — LoRa remains the primary command channel.
 * When WiFi is available the prop posts status updates directly to the
 * backend REST API:  POST /api/props/status-report
 *
 * Set USE_WIFI 1 in your sketch config to enable.
 * Set USE_WIFI 0 (default) to skip entirely and save flash/RAM.
 *
 * Required:  WiFi.h, HTTPClient.h  (bundled with ESP32 Arduino core)
 * ─────────────────────────────────────────────────────────────────────────────
 */
#pragma once

#if defined(USE_WIFI) && USE_WIFI == 1

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

// ─────────────────────────────────────────────────────────────────────────────
// AojWiFi class
// ─────────────────────────────────────────────────────────────────────────────

class AojWiFi {
public:
  // Call once in setup() after serial init.
  // ssid / password: your field WiFi network.
  // serverUrl: base URL of the AOJ backend, e.g. "http://192.168.1.100:8000"
  // propToken:  X-Prop-Token value from the AOJ admin (leave blank if not set)
  void begin(const char *ssid, const char *password,
             const char *serverUrl, const char *propToken = "") {
    _ssid      = ssid;
    _password  = password;
    _serverUrl = serverUrl;
    _token     = propToken;

    WiFi.mode(WIFI_STA);
    WiFi.begin(_ssid, _password);
    Serial.print("[WIFI] Connecting");
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < 10000) {
      delay(500);
      Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("\n[WIFI] Connected — IP: ");
      Serial.println(WiFi.localIP());
      _connected = true;
    } else {
      Serial.println("\n[WIFI] Failed — running LoRa-only");
      _connected = false;
    }
  }

  bool isConnected() {
    _connected = (WiFi.status() == WL_CONNECTED);
    return _connected;
  }

  // POST a status report to /api/props/status-report
  // status:    "online" | "armed" | "disarmed" | "alarm" | etc.
  // battery:   0-100 %
  // signal:    0-100 % (use AojLoRa::rssiPercent() or pass 100 for WiFi-only)
  // fwVersion: firmware version string
  bool reportStatus(const char *deviceId, const char *status,
                    int battery, int signal, const char *fwVersion = "1.0.0") {
    if (!isConnected()) return false;

    HTTPClient http;
    String url = String(_serverUrl) + "/api/props/status-report";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    if (_token && strlen(_token) > 0) {
      http.addHeader("X-Prop-Token", _token);
    }

    // Build JSON manually — no ArduinoJson dependency required.
    String body = "{\"device_id\":\"" + String(deviceId) + "\","
                  "\"status\":\"" + String(status) + "\","
                  "\"battery_level\":" + String(battery) + ","
                  "\"signal_strength\":" + String(signal) + ","
                  "\"firmware_version\":\"" + String(fwVersion) + "\","
                  "\"transport\":\"wifi\"}";

    int code = http.POST(body);
    http.end();

    if (code == 200 || code == 201) {
      Serial.println("[WIFI] Status reported OK");
      return true;
    }
    Serial.print("[WIFI] Status report failed: HTTP "); Serial.println(code);
    return false;
  }

private:
  const char *_ssid     = nullptr;
  const char *_password = nullptr;
  const char *_serverUrl = nullptr;
  const char *_token    = nullptr;
  bool _connected       = false;
};

#else

// ─────────────────────────────────────────────────────────────────────────────
// Stub when WiFi is disabled — all calls compile away to nothing.
// ─────────────────────────────────────────────────────────────────────────────
class AojWiFi {
public:
  void begin(const char *, const char *, const char *, const char * = "") {}
  bool isConnected() { return false; }
  bool reportStatus(const char *, const char *, int, int, const char * = "") { return false; }
};

#endif // USE_WIFI
