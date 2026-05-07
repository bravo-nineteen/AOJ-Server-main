/**
 * GM_Unit.ino
 *
 * Heltec WiFi LoRa 32 V3 horn/siren unit (GM_Unit).
 *
 * Behavior:
 * - LoRa command control via AOJ protocol.
 * - 10 second buzzer countdown, then 3 second relay horn pulse for GAME_START/GAME_END.
 * - Immediate 3 second relay horn pulse for bomb/alarm events.
 * - Optional dedicated WiFi remote activation endpoint (separate SSID/pass/token settings).
 *
 */

#define BOARD_HELTEC_V3

#define DEVICE_ID          "GM_Unit"
#define PROP_TYPE          "GMSirenV3"
#define FW_VERSION         "1.0.0"

// AOJ WiFi status transport is optional and disabled by default here.
#define USE_WIFI           0
#define WIFI_SSID          "AOJ_Server"
#define WIFI_PASS          "AOJ2023"
#define SERVER_URL         "http://192.168.1.100:8000"
#define PROP_TOKEN         ""

#define LORA_FREQUENCY     923.0
#define BATTERY_ADC_PIN    1

#include <WiFi.h>
#include <WebServer.h>
#include <AOJ_Core.h>

// -----------------------------------------------------------------------------
// Hardware pins (adjust to your wiring)
// -----------------------------------------------------------------------------
#define BUZZER_PIN               47
#define RELAY_PIN                36

// -----------------------------------------------------------------------------
// Siren behavior
// -----------------------------------------------------------------------------
#define COUNTDOWN_SECONDS        10
#define COUNTDOWN_BEEP_MS        110
#define FINAL_BEEP_MS            300
#define HORN_PULSE_MS            3000UL
#define HEARTBEAT_INTERVAL_MS    30000UL

// -----------------------------------------------------------------------------
// Dedicated WiFi remote control settings (separate from other props)
// -----------------------------------------------------------------------------
#define REMOTE_WIFI_ENABLED      1
#define REMOTE_WIFI_SSID         "AOJ_GM_REMOTE"
#define REMOTE_WIFI_PASS         "GM_Remote_2026"
#define REMOTE_HTTP_PORT         8081
#define REMOTE_API_TOKEN         "change-me"
#define REMOTE_WIFI_AP_FALLBACK  1

AojLoRa lora;
AojWiFi aojWifi;
WebServer remoteServer(REMOTE_HTTP_PORT);

bool countdownActive = false;
bool hornActive = false;
unsigned long countdownStartMs = 0;
int lastCountdownSecond = -1;
unsigned long hornStartMs = 0;
unsigned long lastHeartbeatMs = 0;
bool loraReady = false;
bool remoteServerActive = false;

String lastTriggerSource = "boot";
String lastAction = "online";

void beep(unsigned int durationMs) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(durationMs);
  digitalWrite(BUZZER_PIN, LOW);
}

void sendFrame(const String &command, const String &value, const String &messageId) {
  if (!loraReady) return;
  String frame = aojBuildFrame(DEVICE_ID, command, value, messageId);
  lora.send(frame);
}

void sendAck(const String &messageId, const String &value = "OK") {
  sendFrame("ACK", value, messageId);
}

void sendEvent(const String &eventType, const String &value) {
  sendFrame(eventType, value, aojGenerateMessageId());
}

void sendStatus() {
  int battery = aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
  int rssi = loraReady ? lora.rssiPercent() : 0;

  String state = "online";
  if (countdownActive) state = "countdown";
  if (hornActive) state = "alarm";

  String value = state + ":" +
                 String(battery) + ":" +
                 String(rssi) + ":" +
                 PROP_TYPE + ":" +
                 lastAction;

  sendFrame("STATUS", value, aojGenerateMessageId());
  aojWifi.reportStatus(DEVICE_ID, state.c_str(), battery, rssi, FW_VERSION);
}

void startHornPulse(const String &source) {
  hornActive = true;
  hornStartMs = millis();
  digitalWrite(RELAY_PIN, HIGH);
  lastTriggerSource = source;
  lastAction = "horn";
  sendEvent("SIREN", "HORN:" + source);
}

void startCountdownThenHorn(const String &source) {
  countdownActive = true;
  countdownStartMs = millis();
  lastCountdownSecond = -1;
  lastTriggerSource = source;
  lastAction = "countdown";
  sendEvent("SIREN", "COUNTDOWN:" + source);
}

void processCountdown() {
  if (!countdownActive) return;

  unsigned long elapsedMs = millis() - countdownStartMs;
  int elapsedSeconds = (int)(elapsedMs / 1000UL);

  if (elapsedSeconds != lastCountdownSecond && elapsedSeconds < COUNTDOWN_SECONDS) {
    int remaining = COUNTDOWN_SECONDS - elapsedSeconds;
    if (remaining <= 1) {
      beep(FINAL_BEEP_MS);
    } else {
      beep(COUNTDOWN_BEEP_MS);
    }
    lastCountdownSecond = elapsedSeconds;
  }

  if (elapsedMs >= (unsigned long)COUNTDOWN_SECONDS * 1000UL) {
    countdownActive = false;
    startHornPulse(lastTriggerSource);
  }
}

void processHorn() {
  if (!hornActive) return;

  if (millis() - hornStartMs >= HORN_PULSE_MS) {
    digitalWrite(RELAY_PIN, LOW);
    hornActive = false;
    lastAction = "online";
    sendEvent("SIREN", "OFF");
  }
}

void triggerIfAuthorized() {
  if (!remoteServer.hasHeader("X-API-Token")) {
    remoteServer.send(401, "application/json", "{\"ok\":false,\"error\":\"missing token\"}");
    return;
  }

  String token = remoteServer.header("X-API-Token");
  if (token != REMOTE_API_TOKEN) {
    remoteServer.send(403, "application/json", "{\"ok\":false,\"error\":\"invalid token\"}");
    return;
  }

  String mode = remoteServer.hasArg("mode") ? remoteServer.arg("mode") : "horn";
  mode.toLowerCase();

  if (mode == "countdown") {
    startCountdownThenHorn("wifi");
    remoteServer.send(200, "application/json", "{\"ok\":true,\"mode\":\"countdown\"}");
    return;
  }

  startHornPulse("wifi");
  remoteServer.send(200, "application/json", "{\"ok\":true,\"mode\":\"horn\"}");
}

void handleRemoteStatus() {
  String payload = "{\"device_id\":\"" + String(DEVICE_ID) +
                   "\",\"countdown\":" + String(countdownActive ? "true" : "false") +
                   ",\"horn\":" + String(hornActive ? "true" : "false") +
                   ",\"last_trigger\":\"" + lastTriggerSource + "\"}";
  remoteServer.send(200, "application/json", payload);
}

void handleRemoteRoot() {
  String body = "GM_Unit remote endpoints:\n"
                "GET /status\n"
                "POST /trigger?mode=horn|countdown\n"
                "POST /test/countdown\n"
                "POST /test/horn\n";
  remoteServer.send(200, "text/plain", body);
}

void setupRemoteServer() {
#if REMOTE_WIFI_ENABLED == 1
  WiFi.mode(WIFI_STA);
  WiFi.begin(REMOTE_WIFI_SSID, REMOTE_WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 12000UL) {
    delay(400);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("\n[REMOTE WIFI] connected IP=");
    Serial.println(WiFi.localIP());

    remoteServer.on("/", HTTP_GET, handleRemoteRoot);
    remoteServer.on("/status", HTTP_GET, handleRemoteStatus);
    remoteServer.on("/trigger", HTTP_POST, triggerIfAuthorized);
    remoteServer.on("/test/countdown", HTTP_POST, []() {
      startCountdownThenHorn("wifi-test");
      remoteServer.send(200, "application/json", "{\"ok\":true}");
    });
    remoteServer.on("/test/horn", HTTP_POST, []() {
      startHornPulse("wifi-test");
      remoteServer.send(200, "application/json", "{\"ok\":true}");
    });
    remoteServer.begin();
    remoteServerActive = true;
    Serial.print("[REMOTE HTTP] listening on ");
    Serial.println(REMOTE_HTTP_PORT);
  } else {
    Serial.println("\n[REMOTE WIFI] connect failed");

#if REMOTE_WIFI_AP_FALLBACK == 1
    WiFi.mode(WIFI_AP);
    bool apOk = WiFi.softAP(REMOTE_WIFI_SSID, REMOTE_WIFI_PASS);
    if (apOk) {
      IPAddress apIp = WiFi.softAPIP();
      Serial.print("[REMOTE AP] fallback online IP=");
      Serial.println(apIp);

      remoteServer.on("/", HTTP_GET, handleRemoteRoot);
      remoteServer.on("/status", HTTP_GET, handleRemoteStatus);
      remoteServer.on("/trigger", HTTP_POST, triggerIfAuthorized);
      remoteServer.on("/test/countdown", HTTP_POST, []() {
        startCountdownThenHorn("wifi-test");
        remoteServer.send(200, "application/json", "{\"ok\":true}");
      });
      remoteServer.on("/test/horn", HTTP_POST, []() {
        startHornPulse("wifi-test");
        remoteServer.send(200, "application/json", "{\"ok\":true}");
      });
      remoteServer.begin();
      remoteServerActive = true;
      Serial.print("[REMOTE HTTP] fallback listening on ");
      Serial.println(REMOTE_HTTP_PORT);
    } else {
      Serial.println("[REMOTE AP] fallback failed, remote HTTP disabled");
    }
#else
    Serial.println("[REMOTE WIFI] remote HTTP disabled");
#endif
  }
#endif
}

void handleLoRaCommand(const AOJFrame &frame) {
  String command = frame.command;
  command.toUpperCase();

  if (command == "STATUS_REQUEST") {
    sendAck(frame.messageId);
    sendStatus();
    return;
  }

  if (command == "GAME_START" || command == "START" || command == "ROUND_START") {
    sendAck(frame.messageId);
    startCountdownThenHorn("lora-game-start");
    return;
  }

  if (command == "GAME_END" || command == "END" || command == "GAMEOVER") {
    sendAck(frame.messageId);
    startCountdownThenHorn("lora-game-end");
    return;
  }

  if (command == "TRIGGER_ALARM" || command == "BOMB_EXPLODED" || command == "EXPLODED" || command == "ALARM") {
    sendAck(frame.messageId);
    startHornPulse("lora-alarm");
    return;
  }

  if (command == "TEST" || command == "SIREN_TEST") {
    sendAck(frame.messageId);
    if (frame.value == "COUNTDOWN") {
      startCountdownThenHorn("lora-test");
    } else {
      startHornPulse("lora-test");
    }
    return;
  }

  sendAck(frame.messageId, "UNKNOWN");
}

void processLoRa() {
  if (!loraReady) return;
  if (!lora.available()) return;

  String raw = lora.read();
  if (raw.length() == 0) return;
  if (!raw.startsWith("AOJ|")) return;

  AOJFrame frame = aojParseFrame(raw);
  if (!frame.valid) return;
  if (frame.deviceId != DEVICE_ID && frame.deviceId != "*") return;

  handleLoRaCommand(frame);
}

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(RELAY_PIN, LOW);

  Serial.begin(115200);
  delay(200);

  Serial.println("[AOJ] GM_Unit siren boot");

  if (lora.begin()) {
    loraReady = true;
    Serial.println("[AOJ] LoRa ready");
  } else {
    loraReady = false;
    Serial.println("[AOJ] LoRa init failed - running in local/offline mode");
  }

  aojWifi.begin(WIFI_SSID, WIFI_PASS, SERVER_URL, PROP_TOKEN);
  setupRemoteServer();

  sendStatus();
  lastHeartbeatMs = millis();
}

void loop() {
  processLoRa();

#if REMOTE_WIFI_ENABLED == 1
  if (remoteServerActive) {
    remoteServer.handleClient();
  }
#endif

  processCountdown();
  processHorn();

  if (millis() - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = millis();
    sendStatus();
  }
}
