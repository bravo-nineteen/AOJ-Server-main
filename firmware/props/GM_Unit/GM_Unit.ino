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
unsigned long hornPulseDurationMs = HORN_PULSE_MS;
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

bool isWifiConnected() {
  return WiFi.status() == WL_CONNECTED || WiFi.getMode() == WIFI_MODE_AP || WiFi.getMode() == WIFI_MODE_APSTA;
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

void startHornPulse(const String &source, unsigned long durationMs) {
  hornActive = true;
  hornStartMs = millis();
  hornPulseDurationMs = durationMs;
  digitalWrite(RELAY_PIN, HIGH);
  lastTriggerSource = source;
  lastAction = "horn";
  sendEvent("SIREN", "HORN:" + source + ":" + String(durationMs));
}

void startHornPulse(const String &source) {
  startHornPulse(source, HORN_PULSE_MS);
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

  if (millis() - hornStartMs >= hornPulseDurationMs) {
    digitalWrite(RELAY_PIN, LOW);
    hornActive = false;
    lastAction = "online";
    sendEvent("SIREN", "OFF");
  }
}

void handleRemoteWifiTest() {
  beep(100);

  String mode = "unknown";
  if (WiFi.getMode() == WIFI_MODE_STA) mode = "sta";
  else if (WiFi.getMode() == WIFI_MODE_AP) mode = "ap";
  else if (WiFi.getMode() == WIFI_MODE_APSTA) mode = "apsta";

  String payload = "{\"ok\":true,\"wifi\":" + String(isWifiConnected() ? "true" : "false") +
                   ",\"mode\":\"" + mode + "\",\"ip\":\"" + WiFi.localIP().toString() + "\"}";
  remoteServer.send(200, "application/json", payload);
}

void handleRemoteBuzzerTest() {
  unsigned int durationMs = 150;
  if (remoteServer.hasArg("ms")) {
    int requested = remoteServer.arg("ms").toInt();
    if (requested >= 20 && requested <= 2000) {
      durationMs = (unsigned int)requested;
    }
  }

  beep(durationMs);
  lastAction = "buzzer-test";
  sendEvent("SIREN", "BUZZER_TEST:" + String(durationMs));
  remoteServer.send(200, "application/json", "{\"ok\":true,\"test\":\"buzzer\",\"ms\":" + String(durationMs) + "}");
}

void handleRemoteHornTest() {
  unsigned long durationMs = HORN_PULSE_MS;
  if (remoteServer.hasArg("ms")) {
    int requested = remoteServer.arg("ms").toInt();
    if (requested >= 100 && requested <= 10000) {
      durationMs = (unsigned long)requested;
    }
  }

  startHornPulse("wifi-test", durationMs);
  remoteServer.send(200, "application/json", "{\"ok\":true,\"test\":\"horn\",\"ms\":" + String(durationMs) + "}");
}

void handleRemoteCountdownTest() {
  startCountdownThenHorn("wifi-test");
  remoteServer.send(200, "application/json", "{\"ok\":true,\"test\":\"countdown\"}");
}

void handleRemoteLoRaTest() {
  if (!loraReady) {
    beep(300);
    remoteServer.send(503, "application/json", "{\"ok\":false,\"test\":\"lora\",\"error\":\"lora_not_ready\"}");
    return;
  }

  // Send a status frame as a simple TX check and chirp to confirm request reached the unit.
  sendStatus();
  sendEvent("SIREN", "LORA_TEST");
  beep(80);

  String payload = "{\"ok\":true,\"test\":\"lora\",\"rssi_percent\":" + String(lora.rssiPercent()) + "}";
  remoteServer.send(200, "application/json", payload);
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

String remoteCss() {
  return R"rawliteral(
<style>
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background: #050505;
  color: #ddd;
  background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
  background-size: 22px 22px;
}
.wrap { max-width: 760px; margin: auto; padding: 18px; }
.brand { color: #d71920; font-size: 24px; font-weight: 900; letter-spacing: 1px; text-transform: uppercase; }
.title { font-size: 34px; font-weight: 900; color: white; margin: 6px 0 18px 0; letter-spacing: 2px; }
.panel { background: #0b0b0b; border: 1px solid #2a2a2a; margin: 14px 0; padding: 14px; box-shadow: 0 0 14px rgba(215,25,32,.16); }
h2 { font-size: 16px; color: #fff; margin: 0 0 12px 0; letter-spacing: 1px; text-transform: uppercase; border-bottom: 1px solid #333; padding-bottom: 8px; }
.row { display: flex; gap: 10px; flex-wrap: wrap; }
.stat { background: #121212; border: 1px solid #333; padding: 10px; flex: 1; min-width: 130px; }
.label { color: #999; font-size: 11px; text-transform: uppercase; }
.value { color: #fff; font-size: 18px; font-weight: 800; margin-top: 4px; }
button {
  background: #d71920;
  color: white;
  border: 0;
  padding: 12px 14px;
  margin: 5px 4px 5px 0;
  font-weight: 900;
  border-radius: 3px;
  letter-spacing: .4px;
  cursor: pointer;
}
button.secondary { background: #222; border: 1px solid #555; }
button.warn { background: #ff9d00; color: #111; }
input[type=number] { background: #111; color: white; border: 1px solid #555; padding: 10px; width: 110px; font-size: 15px; }
.small { font-size: 12px; color: #aaa; }
.ok { color: #67d667; }
.bad { color: #ff6666; }
</style>
)rawliteral";
}

String remotePage() {
  String page = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  page += remoteCss();
  page += "</head><body><div class='wrap'>";

  page += "<div class='brand'>Airsoft Online Japan</div>";
  page += "<div class='title'>GM UNIT CONTROL</div>";

  page += "<div class='panel'><h2>Status</h2><div class='row'>";
  page += "<div class='stat'><div class='label'>Device</div><div class='value' id='deviceId'>" + String(DEVICE_ID) + "</div></div>";
  page += "<div class='stat'><div class='label'>Countdown</div><div class='value' id='countdownState'>-</div></div>";
  page += "<div class='stat'><div class='label'>Horn Relay</div><div class='value' id='hornState'>-</div></div>";
  page += "<div class='stat'><div class='label'>Last Trigger</div><div class='value' id='lastTrigger'>-</div></div>";
  page += "</div>";
  page += "<div class='small'>Tip: open this page from phone/laptop connected to GM WiFi and run tests below.</div></div>";

  page += "<div class='panel'><h2>Quick Tests</h2>";
  page += "<button class='secondary' onclick='runTest(\"/test/wifi\")'>WiFi Test</button>";
  page += "<button onclick='runTest(\"/test/buzzer?ms=150\")'>Buzzer 150 ms</button>";
  page += "<button onclick='runTest(\"/test/relay?ms=3000\")'>Relay/Horn 3 s</button>";
  page += "<button class='warn' onclick='runTest(\"/test/countdown\")'>Countdown then Horn</button>";
  page += "<button class='secondary' onclick='runTest(\"/test/lora\")'>LoRa TX Test</button>";
  page += "</div>";

  page += "<div class='panel'><h2>Custom Duration Tests</h2>";
  page += "<div class='row'>";
  page += "<div class='stat'><div class='label'>Buzzer ms</div><input id='buzzerMs' type='number' min='20' max='2000' value='250'><br><button onclick='runBuzzerCustom()'>Run Buzzer</button></div>";
  page += "<div class='stat'><div class='label'>Horn/Relay ms</div><input id='hornMs' type='number' min='100' max='10000' value='3000'><br><button onclick='runHornCustom()'>Run Horn Relay</button></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Response</h2><div id='result' class='small'>Waiting...</div></div>";

  page += R"rawliteral(
<script>
async function runTest(path) {
  const out = document.getElementById('result');
  out.textContent = 'Requesting ' + path + ' ...';
  try {
    const res = await fetch(path, { method: 'GET' });
    const text = await res.text();
    out.innerHTML = '<span class="' + (res.ok ? 'ok' : 'bad') + '">' + res.status + '</span> ' + text;
    setTimeout(refreshStatus, 120);
  } catch (err) {
    out.innerHTML = '<span class="bad">ERROR</span> ' + err;
  }
}

function runBuzzerCustom() {
  const ms = document.getElementById('buzzerMs').value || '150';
  runTest('/test/buzzer?ms=' + encodeURIComponent(ms));
}

function runHornCustom() {
  const ms = document.getElementById('hornMs').value || '3000';
  runTest('/test/relay?ms=' + encodeURIComponent(ms));
}

async function refreshStatus() {
  try {
    const res = await fetch('/status');
    const data = await res.json();
    document.getElementById('deviceId').textContent = data.device_id || '-';
    document.getElementById('countdownState').textContent = data.countdown ? 'ACTIVE' : 'IDLE';
    document.getElementById('hornState').textContent = data.horn ? 'ON' : 'OFF';
    document.getElementById('lastTrigger').textContent = data.last_trigger || '-';
  } catch (err) {
    document.getElementById('result').innerHTML = '<span class="bad">STATUS ERROR</span> ' + err;
  }
}

refreshStatus();
setInterval(refreshStatus, 2000);
</script>
)rawliteral";

  page += "</div></body></html>";
  return page;
}

void handleRemoteRoot() {
  remoteServer.send(200, "text/html", remotePage());
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
    remoteServer.on("/test/wifi", HTTP_GET, handleRemoteWifiTest);
    remoteServer.on("/test/buzzer", HTTP_GET, handleRemoteBuzzerTest);
    remoteServer.on("/test/buzzer", HTTP_POST, handleRemoteBuzzerTest);
    remoteServer.on("/test/countdown", HTTP_GET, handleRemoteCountdownTest);
    remoteServer.on("/test/countdown", HTTP_POST, handleRemoteCountdownTest);
    remoteServer.on("/test/horn", HTTP_GET, handleRemoteHornTest);
    remoteServer.on("/test/horn", HTTP_POST, handleRemoteHornTest);
    remoteServer.on("/test/relay", HTTP_GET, handleRemoteHornTest);
    remoteServer.on("/test/relay", HTTP_POST, handleRemoteHornTest);
    remoteServer.on("/test/lora", HTTP_GET, handleRemoteLoRaTest);
    remoteServer.on("/test/lora", HTTP_POST, handleRemoteLoRaTest);
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
      remoteServer.on("/test/wifi", HTTP_GET, handleRemoteWifiTest);
      remoteServer.on("/test/buzzer", HTTP_GET, handleRemoteBuzzerTest);
      remoteServer.on("/test/buzzer", HTTP_POST, handleRemoteBuzzerTest);
      remoteServer.on("/test/countdown", HTTP_GET, handleRemoteCountdownTest);
      remoteServer.on("/test/countdown", HTTP_POST, handleRemoteCountdownTest);
      remoteServer.on("/test/horn", HTTP_GET, handleRemoteHornTest);
      remoteServer.on("/test/horn", HTTP_POST, handleRemoteHornTest);
      remoteServer.on("/test/relay", HTTP_GET, handleRemoteHornTest);
      remoteServer.on("/test/relay", HTTP_POST, handleRemoteHornTest);
      remoteServer.on("/test/lora", HTTP_GET, handleRemoteLoRaTest);
      remoteServer.on("/test/lora", HTTP_POST, handleRemoteLoRaTest);
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

  if (command == "GAME_END" || command == "GAME_OVER" || command == "END" || command == "GAMEOVER") {
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
    String testValue = frame.value;
    testValue.toUpperCase();

    if (testValue == "COUNTDOWN") {
      startCountdownThenHorn("lora-test");
    } else if (testValue == "BUZZ" || testValue == "BUZZER" || testValue == "BUZZER_TEST") {
      beep(150);
      lastAction = "buzzer-test";
      sendEvent("SIREN", "BUZZER_TEST:150");
    } else if (testValue == "HORN" || testValue == "RELAY" || testValue == "HORN_TEST") {
      startHornPulse("lora-test", HORN_PULSE_MS);
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
