#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <U8g2lib.h>
#include <Keypad.h>
#include <RadioLib.h>

// =====================================================
// AOJ SAFE AIRSOFT VEST PROP - WIFI CONTROL VERSION
// Heltec WiFi LoRa 32 V3 / ESP32-S3
//
// Relay output is for horn/sounder only.
// Do not connect this to pyrotechnics, ignition devices,
// gas systems, or anything capable of injury.
// =====================================================

// -------------------- USER SETTINGS --------------------

#define UNIT_ID "VEST01"
#define NETWORK_ID "AOJ"
#define REMOTE_KEY "RAVEN19"

const char* WIFI_SSID = "AOJ_VEST01";
const char* WIFI_PASSWORD = "raven1975";

// Default settings. These can be changed in the browser panel.
String disarmCode = "1975";
int correctWireNumber = 3;
unsigned long configuredStartSeconds = 10UL * 60UL;

// Relay behaviour
const bool RELAY_ACTIVE_LOW = true;
const unsigned long HORN_DURATION_MS = 8000;

// LoRa frequency.
// Use only frequencies/settings legal for your module and location.
#define LORA_FREQ 920.6

// -------------------- PIN MAP --------------------

// Heltec V3 LoRa SX1262 pins
#define LORA_NSS   8
#define LORA_DIO1  14
#define LORA_RST   12
#define LORA_BUSY  13
#define LORA_SCK   9
#define LORA_MISO  11
#define LORA_MOSI  10

// External 2.42 inch I2C OLED
#define OLED_SDA 17
#define OLED_SCL 18

// LEDs
#define LED_GREEN  39
#define LED_YELLOW 40
#define LED_RED    41

// Buzzer
#define BUZZER_PIN 42

// Relay output for horn
#define RELAY_PIN 47

// Wire loop inputs
const byte NUM_WIRES = 6;
const byte WIRE_PINS[NUM_WIRES] = {33, 34, 35, 36, 37, 38};

// 4x3 keypad
const byte ROWS = 4;
const byte COLS = 3;

byte rowPins[ROWS] = {1, 2, 3, 4};
byte colPins[COLS] = {5, 6, 7};

char keys[ROWS][COLS] = {
  {'1', '2', '3'},
  {'4', '5', '6'},
  {'7', '8', '9'},
  {'*', '0', '#'}
};

// -------------------- OBJECTS --------------------

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// For SSD1309 128x64 2.42" OLED.
// If your display is SH1106 instead, replace this constructor with:
// U8G2_SH1106_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);
U8G2_SSD1309_128X64_NONAME0_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);

WebServer server(80);
Preferences prefs;

// -------------------- GAME STATE --------------------

enum GameState {
  STATE_SAFE,
  STATE_ARMED,
  STATE_DISARMED,
  STATE_TRIGGERED
};

GameState state = STATE_SAFE;

float timerRate = 1.0;
float remainingSeconds = 0;

int mistakeCount = 0;
String codeInput = "";

bool wireRemovedAlready[NUM_WIRES];
bool previousWireInstalled[NUM_WIRES];

unsigned long lastTimerUpdate = 0;
unsigned long lastBeep = 0;
unsigned long lastDisplayUpdate = 0;
unsigned long hornStartedAt = 0;
unsigned long lastStatusSend = 0;

bool hornActive = false;

// -------------------- BASIC HELPERS --------------------

void setRelay(bool on) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, on ? LOW : HIGH);
  } else {
    digitalWrite(RELAY_PIN, on ? HIGH : LOW);
  }
}

void buzzerOn() {
  digitalWrite(BUZZER_PIN, HIGH);
}

void buzzerOff() {
  digitalWrite(BUZZER_PIN, LOW);
}

void beep(unsigned int durationMs) {
  buzzerOn();
  delay(durationMs);
  buzzerOff();
}

void errorNoise() {
  for (int i = 0; i < 3; i++) {
    beep(80);
    delay(70);
  }
}

void successNoise() {
  beep(120);
  delay(80);
  beep(120);
  delay(80);
  beep(300);
}

void triggeredNoise() {
  for (int i = 0; i < 8; i++) {
    beep(120);
    delay(80);
  }
}

String stateName() {
  if (state == STATE_SAFE) return "SAFE";
  if (state == STATE_ARMED) return "ARMED";
  if (state == STATE_DISARMED) return "DISARMED";
  if (state == STATE_TRIGGERED) return "TRIGGERED";
  return "UNKNOWN";
}

String formatTime(float secondsValue) {
  if (secondsValue < 0) secondsValue = 0;

  int total = (int)secondsValue;
  int minutes = total / 60;
  int seconds = total % 60;

  char buffer[10];
  snprintf(buffer, sizeof(buffer), "%02d:%02d", minutes, seconds);
  return String(buffer);
}

bool allWiresInstalled() {
  for (int i = 0; i < NUM_WIRES; i++) {
    if (digitalRead(WIRE_PINS[i]) != LOW) {
      return false;
    }
  }

  return true;
}

String wireStatusText() {
  String text = "";

  for (int i = 0; i < NUM_WIRES; i++) {
    bool installed = digitalRead(WIRE_PINS[i]) == LOW;

    text += "W";
    text += String(i + 1);
    text += ":";
    text += installed ? "IN" : "OUT";

    if (i < NUM_WIRES - 1) text += " ";
  }

  return text;
}

void setLeds() {
  if (state == STATE_SAFE) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, HIGH);
    digitalWrite(LED_RED, LOW);
    return;
  }

  if (state == STATE_DISARMED) {
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, LOW);
    return;
  }

  if (state == STATE_TRIGGERED) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    return;
  }

  if (state == STATE_ARMED) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_RED, HIGH);

    if (mistakeCount > 0 || remainingSeconds <= 60) {
      digitalWrite(LED_YELLOW, (millis() / 300) % 2);
    } else {
      digitalWrite(LED_YELLOW, LOW);
    }
  }
}

// -------------------- SETTINGS STORAGE --------------------

void loadSettings() {
  prefs.begin("aojvest", false);

  disarmCode = prefs.getString("code", "1975");
  correctWireNumber = prefs.getInt("wire", 3);
  configuredStartSeconds = prefs.getULong("timer", 600);

  if (correctWireNumber < 1 || correctWireNumber > 6) {
    correctWireNumber = 3;
  }

  if (configuredStartSeconds < 10) {
    configuredStartSeconds = 10;
  }

  if (configuredStartSeconds > 3600) {
    configuredStartSeconds = 3600;
  }

  prefs.end();
}

void saveSettings() {
  prefs.begin("aojvest", false);

  prefs.putString("code", disarmCode);
  prefs.putInt("wire", correctWireNumber);
  prefs.putULong("timer", configuredStartSeconds);

  prefs.end();
}

// -------------------- LORA --------------------

void sendLoraMessage(String command) {
  String packet = String(NETWORK_ID) + "|" + String(UNIT_ID) + "|" + command;
  radio.transmit(packet);
  radio.startReceive();
}

bool packetMatchesThisUnit(String packet) {
  packet.trim();

  String prefix1 = String(NETWORK_ID) + "|" + String(UNIT_ID) + "|";
  String prefix2 = String(NETWORK_ID) + "|ALL|";

  return packet.startsWith(prefix1) || packet.startsWith(prefix2);
}

// -------------------- GAME ACTIONS --------------------

void activateHorn(String reason) {
  if (state == STATE_TRIGGERED) return;

  state = STATE_TRIGGERED;
  hornActive = true;
  hornStartedAt = millis();

  setRelay(true);
  setLeds();

  sendLoraMessage("TRIGGERED:" + reason);
  triggeredNoise();
}

void disarmUnit(String method) {
  if (state != STATE_ARMED && state != STATE_TRIGGERED) {
    state = STATE_DISARMED;
  } else {
    state = STATE_DISARMED;
  }

  hornActive = false;
  setRelay(false);
  buzzerOff();
  setLeds();

  sendLoraMessage("DISARMED:" + method);
  successNoise();
}

bool armUnit() {
  if (!allWiresInstalled()) {
    errorNoise();
    return false;
  }

  state = STATE_ARMED;
  timerRate = 1.0;
  remainingSeconds = configuredStartSeconds;
  mistakeCount = 0;
  codeInput = "";
  hornActive = false;

  setRelay(false);
  buzzerOff();

  for (int i = 0; i < NUM_WIRES; i++) {
    wireRemovedAlready[i] = false;
    previousWireInstalled[i] = digitalRead(WIRE_PINS[i]) == LOW;
  }

  lastTimerUpdate = millis();
  lastBeep = millis();

  setLeds();
  sendLoraMessage("ARMED");
  beep(250);

  return true;
}

void resetToSafe() {
  state = STATE_SAFE;
  timerRate = 1.0;
  remainingSeconds = configuredStartSeconds;
  mistakeCount = 0;
  codeInput = "";
  hornActive = false;

  setRelay(false);
  buzzerOff();
  setLeds();

  sendLoraMessage("SAFE");
}

void applyMistakePenalty(String reason) {
  if (state != STATE_ARMED) return;

  mistakeCount++;

  errorNoise();
  sendLoraMessage("MISTAKE:" + String(mistakeCount) + ":" + reason);

  if (mistakeCount == 1) {
    timerRate = 2.0;
  } else if (mistakeCount == 2) {
    remainingSeconds *= 0.75;
  } else {
    activateHorn("TOO_MANY_MISTAKES");
  }
}

// -------------------- INPUT HANDLING --------------------

void checkKeypad() {
  char key = keypad.getKey();

  if (!key || state != STATE_ARMED) return;

  if (key >= '0' && key <= '9') {
    if (codeInput.length() < 8) {
      codeInput += key;
      beep(30);
    }
  }

  if (key == '*') {
    codeInput = "";
    beep(50);
  }

  if (key == '#') {
    if (codeInput.equals(disarmCode)) {
      disarmUnit("CODE");
    } else {
      codeInput = "";
      applyMistakePenalty("WRONG_CODE");
    }
  }
}

void checkWires() {
  if (state != STATE_ARMED) return;

  for (int i = 0; i < NUM_WIRES; i++) {
    bool installedNow = digitalRead(WIRE_PINS[i]) == LOW;

    if (previousWireInstalled[i] == true && installedNow == false) {
      if (!wireRemovedAlready[i]) {
        wireRemovedAlready[i] = true;

        int wireNumber = i + 1;

        if (wireNumber == correctWireNumber) {
          disarmUnit("WIRE_" + String(wireNumber));
        } else {
          applyMistakePenalty("WRONG_WIRE_" + String(wireNumber));
        }
      }
    }

    previousWireInstalled[i] = installedNow;
  }
}

// -------------------- TIMER / OUTPUT --------------------

void updateTimer() {
  if (state != STATE_ARMED) return;

  unsigned long now = millis();

  if (lastTimerUpdate == 0) {
    lastTimerUpdate = now;
    return;
  }

  float elapsed = (now - lastTimerUpdate) / 1000.0;
  lastTimerUpdate = now;

  remainingSeconds -= elapsed * timerRate;

  if (remainingSeconds <= 0) {
    remainingSeconds = 0;
    activateHorn("TIME_EXPIRED");
  }
}

void updateBeeps() {
  if (state != STATE_ARMED) return;

  unsigned long now = millis();

  unsigned long interval = 1000;

  if (mistakeCount >= 1) interval = 500;
  if (remainingSeconds <= 60) interval = 300;
  if (remainingSeconds <= 20) interval = 150;

  if (now - lastBeep >= interval) {
    lastBeep = now;
    beep(35);
  }
}

void updateHorn() {
  if (!hornActive) return;

  if (millis() - hornStartedAt >= HORN_DURATION_MS) {
    hornActive = false;
    setRelay(false);
  }
}

void checkLora() {
  String incoming = "";
  int result = radio.receive(incoming, 5);

  if (result == RADIOLIB_ERR_NONE) {
    incoming.trim();

    if (packetMatchesThisUnit(incoming)) {
      if (incoming.indexOf("REMOTE_TRIGGER:" + String(REMOTE_KEY)) >= 0) {
        activateHorn("REMOTE");
      }

      if (incoming.indexOf("REMOTE_DISARM:" + String(REMOTE_KEY)) >= 0) {
        disarmUnit("REMOTE");
      }

      if (incoming.indexOf("STATUS_REQUEST") >= 0) {
        sendLoraMessage("STATUS:" + stateName() + ":TIME:" + formatTime(remainingSeconds));
      }
    }
  }

  radio.startReceive();
}

void sendStatusOccasionally() {
  if (millis() - lastStatusSend < 15000) return;

  lastStatusSend = millis();

  String statusText;

  if (state == STATE_ARMED) {
    statusText = "ARMED:" + formatTime(remainingSeconds) + ":MISTAKES:" + String(mistakeCount);
  } else {
    statusText = stateName();
  }

  sendLoraMessage("STATUS:" + statusText);
}

// -------------------- OLED DISPLAY --------------------

void drawDisplay() {
  if (millis() - lastDisplayUpdate < 150) return;
  lastDisplayUpdate = millis();

  display.clearBuffer();

  display.setFont(u8g2_font_6x12_tf);
  display.drawStr(0, 10, "AOJ VEST UNIT");
  display.drawHLine(0, 13, 128);

  if (state == STATE_SAFE) {
    display.setFont(u8g2_font_9x15B_tf);
    display.drawStr(30, 33, "SAFE");
    display.setFont(u8g2_font_6x12_tf);
    display.drawStr(0, 50, "WiFi: AOJ_VEST01");
    display.drawStr(0, 62, "192.168.4.1");
  }

  if (state == STATE_ARMED) {
    display.setFont(u8g2_font_logisoso24_tf);
    String timeText = formatTime(remainingSeconds);
    display.drawStr(18, 42, timeText.c_str());

    display.setFont(u8g2_font_6x12_tf);

    String codeLine = "CODE: ";
    for (unsigned int i = 0; i < codeInput.length(); i++) {
      codeLine += "*";
    }

    display.drawStr(0, 56, codeLine.c_str());

    String m = "ERR:";
    m += mistakeCount;
    m += " RATE:";
    m += String(timerRate, 1);
    display.drawStr(0, 64, m.c_str());
  }

  if (state == STATE_DISARMED) {
    display.setFont(u8g2_font_9x15B_tf);
    display.drawStr(20, 36, "DISARMED");
    display.setFont(u8g2_font_6x12_tf);
    display.drawStr(15, 55, "UNIT SAFE");
  }

  if (state == STATE_TRIGGERED) {
    display.setFont(u8g2_font_9x15B_tf);
    display.drawStr(18, 34, "GAME OVER");
    display.setFont(u8g2_font_6x12_tf);
    display.drawStr(10, 55, "HORN ACTIVATED");
  }

  display.sendBuffer();
}

void bootScreen() {
  display.clearBuffer();
  display.setFont(u8g2_font_6x12_tf);
  display.drawStr(0, 12, "AOJ VEST UNIT");
  display.drawStr(0, 28, "Created by Nineteen");
  display.drawStr(0, 44, "System starting...");
  display.drawFrame(0, 54, 128, 8);

  for (int i = 0; i <= 124; i += 4) {
    display.drawBox(2, 56, i, 4);
    display.sendBuffer();
    delay(25);
  }
}

// -------------------- WIFI WEB CONTROL --------------------

String htmlPage() {
  String page = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AOJ Vest Control</title>
<style>
body {
  font-family: Arial, sans-serif;
  background: #111;
  color: #eee;
  margin: 0;
  padding: 16px;
}
.card {
  background: #1d1d1d;
  border: 1px solid #333;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
}
h1 {
  font-size: 24px;
  margin: 0 0 12px 0;
}
h2 {
  font-size: 18px;
  margin: 0 0 10px 0;
}
input, select {
  width: 100%;
  padding: 12px;
  margin: 6px 0 12px 0;
  border-radius: 10px;
  border: 1px solid #555;
  background: #050505;
  color: #fff;
  font-size: 16px;
  box-sizing: border-box;
}
button {
  width: 100%;
  padding: 14px;
  margin: 6px 0;
  border: 0;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
}
.green { background: #1f7a3a; }
.yellow { background: #9a7500; }
.red { background: #a12121; }
.blue { background: #285ea8; }
.grey { background: #555; }
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.status {
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-line;
}
.small {
  font-size: 13px;
  color: #aaa;
}
</style>
</head>
<body>

<h1>AOJ Vest Control</h1>

<div class="card">
  <h2>Status</h2>
  <div id="status" class="status">Loading...</div>
</div>

<div class="card">
  <h2>Setup</h2>

  <label>Disarm Code</label>
  <input id="code" type="text" inputmode="numeric" maxlength="8">

  <label>Timer Minutes</label>
  <input id="timer" type="number" min="1" max="60">

  <label>Correct Wire</label>
  <select id="wire">
    <option value="1">Wire 1</option>
    <option value="2">Wire 2</option>
    <option value="3">Wire 3</option>
    <option value="4">Wire 4</option>
    <option value="5">Wire 5</option>
    <option value="6">Wire 6</option>
  </select>

  <button class="blue" onclick="saveSettings()">Save Settings</button>
  <div class="small">Settings are saved to device memory.</div>
</div>

<div class="card">
  <h2>Game Control</h2>
  <button class="red" onclick="cmd('/api/arm')">ARM UNIT</button>
  <button class="green" onclick="cmd('/api/disarm')">DISARM UNIT</button>
  <button class="grey" onclick="cmd('/api/reset')">RESET TO SAFE</button>
  <button class="red" onclick="confirmHorn()">MANUAL HORN</button>
</div>

<div class="card">
  <h2>System Tests</h2>
  <div class="row">
    <button class="yellow" onclick="cmd('/api/test/buzzer')">Buzzer</button>
    <button class="yellow" onclick="cmd('/api/test/leds')">LEDs</button>
  </div>
  <button class="yellow" onclick="cmd('/api/test/relay')">Relay / Horn Test</button>
</div>

<script>
async function cmd(url) {
  await fetch(url);
  await refreshStatus();
}

async function saveSettings() {
  const code = document.getElementById('code').value;
  const timer = document.getElementById('timer').value;
  const wire = document.getElementById('wire').value;

  await fetch(`/api/save?code=${encodeURIComponent(code)}&timer=${encodeURIComponent(timer)}&wire=${encodeURIComponent(wire)}`);
  await refreshStatus();
}

async function confirmHorn() {
  if (confirm("Activate horn manually?")) {
    await cmd('/api/horn');
  }
}

async function refreshStatus() {
  const res = await fetch('/api/status');
  const data = await res.json();

  document.getElementById('status').innerText =
    "State: " + data.state + "\n" +
    "Time: " + data.time + "\n" +
    "Mistakes: " + data.mistakes + "\n" +
    "Timer Rate: x" + data.rate + "\n" +
    "Code: " + data.code + "\n" +
    "Correct Wire: " + data.correctWire + "\n" +
    "Wires: " + data.wires + "\n" +
    "WiFi IP: 192.168.4.1";

  document.getElementById('code').value = data.code;
  document.getElementById('timer').value = data.timerMinutes;
  document.getElementById('wire').value = data.correctWire;
}

setInterval(refreshStatus, 1000);
refreshStatus();
</script>

</body>
</html>
)rawliteral";

  return page;
}

void handleRoot() {
  server.send(200, "text/html", htmlPage());
}

void handleStatus() {
  String json = "{";
  json += "\"state\":\"" + stateName() + "\",";
  json += "\"time\":\"" + formatTime(remainingSeconds) + "\",";
  json += "\"mistakes\":" + String(mistakeCount) + ",";
  json += "\"rate\":\"" + String(timerRate, 1) + "\",";
  json += "\"code\":\"" + disarmCode + "\",";
  json += "\"correctWire\":" + String(correctWireNumber) + ",";
  json += "\"timerMinutes\":" + String(configuredStartSeconds / 60) + ",";
  json += "\"wires\":\"" + wireStatusText() + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

void handleSave() {
  if (server.hasArg("code")) {
    String newCode = server.arg("code");
    newCode.trim();

    if (newCode.length() >= 1 && newCode.length() <= 8) {
      disarmCode = newCode;
    }
  }

  if (server.hasArg("timer")) {
    int minutes = server.arg("timer").toInt();

    if (minutes < 1) minutes = 1;
    if (minutes > 60) minutes = 60;

    configuredStartSeconds = (unsigned long)minutes * 60UL;

    if (state == STATE_SAFE || state == STATE_DISARMED) {
      remainingSeconds = configuredStartSeconds;
    }
  }

  if (server.hasArg("wire")) {
    int wire = server.arg("wire").toInt();

    if (wire >= 1 && wire <= 6) {
      correctWireNumber = wire;
    }
  }

  saveSettings();
  server.send(200, "text/plain", "Settings saved");
}

void handleArm() {
  bool armed = armUnit();

  if (armed) {
    server.send(200, "text/plain", "Unit armed");
  } else {
    server.send(409, "text/plain", "Cannot arm. All wires must be connected first.");
  }
}

void handleDisarm() {
  disarmUnit("WEB");
  server.send(200, "text/plain", "Unit disarmed");
}

void handleReset() {
  resetToSafe();
  server.send(200, "text/plain", "Unit reset to safe");
}

void handleHorn() {
  activateHorn("WEB_MANUAL");
  server.send(200, "text/plain", "Horn activated");
}

void handleTestBuzzer() {
  beep(100);
  delay(100);
  beep(100);
  delay(100);
  beep(250);

  server.send(200, "text/plain", "Buzzer tested");
}

void handleTestLeds() {
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, LOW);
  delay(400);

  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_YELLOW, HIGH);
  digitalWrite(LED_RED, LOW);
  delay(400);

  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, HIGH);
  delay(400);

  setLeds();

  server.send(200, "text/plain", "LEDs tested");
}

void handleTestRelay() {
  setRelay(true);
  delay(1000);
  setRelay(false);

  server.send(200, "text/plain", "Relay tested");
}

void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_PASSWORD);

  server.on("/", handleRoot);
  server.on("/api/status", handleStatus);
  server.on("/api/save", handleSave);
  server.on("/api/arm", handleArm);
  server.on("/api/disarm", handleDisarm);
  server.on("/api/reset", handleReset);
  server.on("/api/horn", handleHorn);
  server.on("/api/test/buzzer", handleTestBuzzer);
  server.on("/api/test/leds", handleTestLeds);
  server.on("/api/test/relay", handleTestRelay);

  server.begin();
}

// -------------------- SETUP --------------------

void setupPins() {
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  setRelay(false);
  buzzerOff();

  for (int i = 0; i < NUM_WIRES; i++) {
    pinMode(WIRE_PINS[i], INPUT_PULLUP);
    wireRemovedAlready[i] = false;
    previousWireInstalled[i] = digitalRead(WIRE_PINS[i]) == LOW;
  }

  setLeds();
}

void setupDisplay() {
  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin();
  display.setContrast(180);
}

void setupRadio() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  int result = radio.begin(
    LORA_FREQ,
    125.0,
    7,
    5,
    0x12,
    14,
    8,
    1.6,
    false
  );

  if (result != RADIOLIB_ERR_NONE) {
    display.clearBuffer();
    display.setFont(u8g2_font_6x12_tf);
    display.drawStr(0, 12, "LoRa failed.");
    display.drawStr(0, 28, "Check module/pins.");
    display.sendBuffer();

    while (true) {
      digitalWrite(LED_YELLOW, HIGH);
      delay(200);
      digitalWrite(LED_YELLOW, LOW);
      delay(200);
    }
  }

  radio.startReceive();
}

void setup() {
  Serial.begin(115200);
  delay(500);

  loadSettings();

  remainingSeconds = configuredStartSeconds;

  setupPins();
  setupDisplay();
  bootScreen();
  setupRadio();
  setupWiFi();

  resetToSafe();

  sendLoraMessage("BOOTED_WIFI_READY");
}

// -------------------- MAIN LOOP --------------------

void loop() {
  server.handleClient();

  checkLora();
  checkKeypad();
  checkWires();

  updateTimer();
  updateBeeps();
  updateHorn();

  setLeds();
  drawDisplay();
  sendStatusOccasionally();
}
