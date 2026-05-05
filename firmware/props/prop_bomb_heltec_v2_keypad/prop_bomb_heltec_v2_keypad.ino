/**
 * prop_bomb_heltec_v2_keypad.ino
 *
 * Heltec WiFi LoRa 32 V2 bomb prop with:
 * - keypad code entry (arm + defuse)
 * - 16x2 I2C LCD UI
 * - EEPROM settings storage
 * - local AP + web config while idle
 * - AOJ LoRa protocol integration for server command/control
 *
 * IMPORTANT PIN NOTE:
 * The original keypad pin set conflicts with Heltec V2 LoRa pins.
 * This version remaps keypad/control GPIO so SX1276 LoRa remains operational.
 */

// -----------------------------------------------------------------------------
// Board / AOJ identity
// -----------------------------------------------------------------------------
#define BOARD_HELTEC_V2

#define DEVICE_ID   "BD-001"
#define PROP_TYPE   "BombKeypadV2"
#define FW_VERSION  "1.0.0"

// Optional AOJ WiFi status reporting (independent of AP config below).
#define USE_WIFI    0
#define WIFI_SSID   "AOJ_Server"
#define WIFI_PASS   "AOJ2023"
#define SERVER_URL  "http://192.168.1.100:8000"
#define PROP_TOKEN  ""

// -----------------------------------------------------------------------------
// Includes
// -----------------------------------------------------------------------------
#include <Keypad.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <WiFi.h>
#include <WebServer.h>
#include <EEPROM.h>
#include <AOJ_Core.h>

// -----------------------------------------------------------------------------
// LCD
// -----------------------------------------------------------------------------
LiquidCrystal_I2C lcd(0x27, 16, 2);

// -----------------------------------------------------------------------------
// KEYPAD (REMAP FOR HELTEC V2 + LORA)
// -----------------------------------------------------------------------------
const byte ROWS = 4;
const byte COLS = 3;

char keys[ROWS][COLS] = {
  {'1', '2', '3'},
  {'4', '5', '6'},
  {'7', '8', '9'},
  {'*', '0', '#'}
};

byte rowPins[ROWS] = {23, 25, 33, 32};
byte colPins[COLS] = {12, 13, 17};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// -----------------------------------------------------------------------------
// HELTEC V2-SAFE GPIO MAP
// -----------------------------------------------------------------------------
const int potPin = 34;        // ADC input only
const int relayPin = 4;
const int redLedPin = 2;
const int buzzerPin = 15;
const int armSwitchPin = 16;

// -----------------------------------------------------------------------------
// WiFi AP / local web settings
// -----------------------------------------------------------------------------
WebServer server(80);
const char* apSSID = "AOJ_CSGO_BOMB";
const char* apPassword = "12345678";

// -----------------------------------------------------------------------------
// EEPROM
// -----------------------------------------------------------------------------
const int EEPROM_SIZE = 128;
const int EEPROM_ADDR = 0;

// -----------------------------------------------------------------------------
// Settings
// -----------------------------------------------------------------------------
struct Settings {
  uint8_t magic;
  uint8_t useRandomCode;
  char presetCode[9];
  uint32_t timerSeconds;
};

Settings settings;

// -----------------------------------------------------------------------------
// Game state
// -----------------------------------------------------------------------------
enum GameState {
  STATE_IDLE,
  STATE_READY_TO_ARM,
  STATE_ARMED,
  STATE_DEFUSED,
  STATE_EXPLODED
};

GameState gameState = STATE_IDLE;

// -----------------------------------------------------------------------------
// Variables
// -----------------------------------------------------------------------------
char activeCode[9] = "00000000";
byte entryIndex = 0;

unsigned long countdownStartMs = 0;
unsigned long relayStartMs = 0;
unsigned long lastBlinkMs = 0;
unsigned long lastBeepMs = 0;
unsigned long lastScreenMs = 0;
unsigned long lastHeartbeatMs = 0;

bool relayActive = false;
bool ledState = false;

const unsigned long HEARTBEAT_INTERVAL_MS = 30000UL;

// -----------------------------------------------------------------------------
// AOJ transport
// -----------------------------------------------------------------------------
AojLoRa lora;
AojWiFi aojWifi;

// -----------------------------------------------------------------------------
// Forward declarations
// -----------------------------------------------------------------------------
void applyDefaultSettings();
void loadSettings();
void saveSettings();

bool isValid8DigitString(const String& s);
void generateRandomCode();
void loadActiveCode();

void resetEntry();
void resetToIdle();
void activateForArming();
void armBomb(bool fromRemote = false);
void defuseBomb(bool fromRemote = false);
void detonateBomb(bool fromRemote = false);

void showIdleScreen();
void showReadyScreen();
void showArmedScreen(unsigned long remainingMs);
void showDefusedScreen();
void showExplodedScreen();
void renderMaskedCode();

void handleReadyInput();
void handleArmedInput();
void updateCountdown();
void updateArmedEffects(unsigned long remainingMs);
void shortBeep(unsigned int durationMs);

void setupWiFiAP();
void setupWebServer();
void processWebServer();
void handleRoot();
void handleSave();
void handleRegenerate();
void handleDetonate();

void sendFrame(const String& command, const String& value, const String& messageId);
void sendAck(const String& messageId, const String& ackValue = "OK");
void sendStatus();
void processLoRa();
void handleServerCommand(const AOJFrame& frame);

const char* stateLabel() {
  switch (gameState) {
    case STATE_ARMED: return "armed";
    case STATE_DEFUSED: return "disarmed";
    case STATE_EXPLODED: return "alarm";
    default: return "online";
  }
}

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  pinMode(relayPin, OUTPUT);
  pinMode(redLedPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  pinMode(armSwitchPin, INPUT_PULLUP);

  digitalWrite(relayPin, LOW);
  digitalWrite(redLedPin, LOW);
  digitalWrite(buzzerPin, LOW);

  // External LCD I2C bus.
  Wire.begin(22, 21);
  lcd.init();
  lcd.backlight();

  Serial.begin(115200);
  delay(200);

  if (!lora.begin()) {
    Serial.println("[AOJ] LoRa init failed - halting");
    while (true) { delay(1000); }
  }

  aojWifi.begin(WIFI_SSID, WIFI_PASS, SERVER_URL, PROP_TOKEN);

  EEPROM.begin(EEPROM_SIZE);
  loadSettings();
  randomSeed(micros());

  setupWiFiAP();
  setupWebServer();

  resetToIdle();
  sendStatus();
  lastHeartbeatMs = millis();
}

// -----------------------------------------------------------------------------
// Loop
// -----------------------------------------------------------------------------
void loop() {
  processLoRa();

  if (gameState == STATE_IDLE) {
    processWebServer();
  }

  if (relayActive && (millis() - relayStartMs >= 3000UL)) {
    digitalWrite(relayPin, LOW);
    digitalWrite(buzzerPin, LOW);
    relayActive = false;
  }

  switch (gameState) {
    case STATE_IDLE:
      if (millis() - lastScreenMs >= 300) {
        showIdleScreen();
        lastScreenMs = millis();
      }
      if (digitalRead(armSwitchPin) == LOW) {
        activateForArming();
        delay(250);
      }
      break;

    case STATE_READY_TO_ARM:
      handleReadyInput();
      break;

    case STATE_ARMED:
      handleArmedInput();
      updateCountdown();
      break;

    case STATE_DEFUSED:
      if (millis() - lastScreenMs >= 400) {
        showDefusedScreen();
        lastScreenMs = millis();
      }
      break;

    case STATE_EXPLODED:
      if (millis() - lastScreenMs >= 400) {
        showExplodedScreen();
        lastScreenMs = millis();
      }
      break;
  }

  if (millis() - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = millis();
    sendStatus();
  }
}

// -----------------------------------------------------------------------------
// AOJ LoRa functions
// -----------------------------------------------------------------------------
void sendFrame(const String& command, const String& value, const String& messageId) {
  String frame = aojBuildFrame(DEVICE_ID, command, value, messageId);
  lora.send(frame);
}

void sendAck(const String& messageId, const String& ackValue) {
  sendFrame("ACK", ackValue, messageId);
}

void sendStatus() {
  int battery = aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
  int rssi = lora.rssiPercent();
  String value = String(stateLabel()) + ":" + String(battery) + ":" + String(rssi) + ":" + PROP_TYPE;
  sendFrame("STATUS", value, aojGenerateMessageId());
  aojWifi.reportStatus(DEVICE_ID, stateLabel(), battery, rssi, FW_VERSION);
}

void processLoRa() {
  if (!lora.available()) {
    return;
  }

  String raw = lora.read();
  if (raw.length() == 0) {
    return;
  }

  AOJFrame frame = aojParseFrame(raw);
  if (!frame.valid) {
    return;
  }

  if (frame.deviceId != DEVICE_ID && frame.deviceId != "*") {
    return;
  }

  handleServerCommand(frame);
}

void handleServerCommand(const AOJFrame& frame) {
  if (frame.command == "ARM") {
    if (frame.value.length() > 0) {
      long sec = frame.value.toInt();
      if (sec >= 5 && sec <= 3600) {
        settings.timerSeconds = (uint32_t)sec;
      }
    }
    armBomb(true);
    sendAck(frame.messageId);
  }
  else if (frame.command == "DISARM") {
    defuseBomb(true);
    sendAck(frame.messageId);
  }
  else if (frame.command == "RESET") {
    resetToIdle();
    sendAck(frame.messageId);
  }
  else if (frame.command == "SET_TIMER") {
    long sec = frame.value.toInt();
    if (sec >= 5 && sec <= 3600) {
      settings.timerSeconds = (uint32_t)sec;
      saveSettings();
    }
    sendAck(frame.messageId);
  }
  else if (frame.command == "TRIGGER_ALARM") {
    detonateBomb(true);
    sendAck(frame.messageId);
  }
  else if (frame.command == "STATUS_REQUEST") {
    sendAck(frame.messageId);
    sendStatus();
  }
  else {
    sendAck(frame.messageId, "UNKNOWN");
  }
}

// -----------------------------------------------------------------------------
// Settings
// -----------------------------------------------------------------------------
void applyDefaultSettings() {
  settings.magic = 0x42;
  settings.useRandomCode = 1;
  strcpy(settings.presetCode, "73556081");
  settings.timerSeconds = 45;
}

void loadSettings() {
  EEPROM.get(EEPROM_ADDR, settings);

  if (settings.magic != 0x42) {
    applyDefaultSettings();
    saveSettings();
  }

  if (settings.timerSeconds < 5 || settings.timerSeconds > 3600) {
    settings.timerSeconds = 45;
    saveSettings();
  }

  String preset = String(settings.presetCode);
  if (!isValid8DigitString(preset)) {
    strcpy(settings.presetCode, "73556081");
    saveSettings();
  }
}

void saveSettings() {
  EEPROM.put(EEPROM_ADDR, settings);
  EEPROM.commit();
}

// -----------------------------------------------------------------------------
// WiFi / Web
// -----------------------------------------------------------------------------
void setupWiFiAP() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(apSSID, apPassword);

  Serial.println();
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());
}

void setupWebServer() {
  server.on("/", handleRoot);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/regenerate", HTTP_GET, handleRegenerate);
  server.on("/detonate", HTTP_GET, handleDetonate);
  server.begin();
}

void processWebServer() {
  server.handleClient();
}

void handleRoot() {
  String html;
  html += "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<title>AOJ Bomb Config</title>";
  html += "<style>";
  html += "body{font-family:Arial;background:#111;color:#eee;padding:20px;}";
  html += ".box{max-width:420px;background:#1b1b1b;padding:16px;border-radius:10px;}";
  html += "input,button{font-size:18px;padding:8px;margin:6px 0;}";
  html += ".danger{background:#a00;color:#fff;border:none;}";
  html += "</style></head><body><div class='box'>";
  html += "<h2>AOJ Bomb Config</h2>";

  html += "<p><b>State:</b> ";
  if (gameState == STATE_IDLE) html += "IDLE";
  else if (gameState == STATE_READY_TO_ARM) html += "READY TO ARM";
  else if (gameState == STATE_ARMED) html += "ARMED";
  else if (gameState == STATE_DEFUSED) html += "DEFUSED";
  else if (gameState == STATE_EXPLODED) html += "EXPLODED";
  html += "</p>";

  html += "<p><b>Mode:</b> ";
  html += settings.useRandomCode ? "Random" : "Preset";
  html += "</p>";

  html += "<p><b>Active Code:</b> ";
  html += activeCode;
  html += "</p>";

  if (gameState == STATE_IDLE) {
    html += "<form method='POST' action='/save'>";

    html += "<label><input type='checkbox' name='random' ";
    if (settings.useRandomCode) html += "checked";
    html += "> Use random code</label><br>";

    html += "<label>Preset 8-digit code</label><br>";
    html += "<input type='text' name='preset' maxlength='8' value='";
    html += settings.presetCode;
    html += "'><br>";

    html += "<label>Timer seconds</label><br>";
    html += "<input type='number' name='seconds' min='5' max='3600' value='";
    html += String(settings.timerSeconds);
    html += "'><br>";

    html += "<button type='submit'>Save Settings</button>";
    html += "</form>";

    html += "<p><a href='/regenerate'><button>Regenerate Random Code</button></a></p>";
  } else {
    html += "<p>Settings locked while game is active.</p>";
  }

  html += "<p><a href='/detonate'><button class='danger'>Instant Detonate</button></a></p>";
  html += "</div></body></html>";

  server.send(200, "text/html", html);
}

void handleSave() {
  if (gameState != STATE_IDLE) {
    server.send(403, "text/plain", "Settings locked while game is active.");
    return;
  }

  settings.useRandomCode = server.hasArg("random") ? 1 : 0;

  if (server.hasArg("preset")) {
    String p = server.arg("preset");
    p.trim();
    if (isValid8DigitString(p)) {
      p.toCharArray(settings.presetCode, sizeof(settings.presetCode));
    }
  }

  if (server.hasArg("seconds")) {
    long sec = server.arg("seconds").toInt();
    if (sec >= 5 && sec <= 3600) {
      settings.timerSeconds = (uint32_t)sec;
    }
  }

  saveSettings();
  loadActiveCode();

  server.sendHeader("Location", "/");
  server.send(303);
}

void handleRegenerate() {
  if (gameState == STATE_IDLE && settings.useRandomCode) {
    generateRandomCode();
  }

  server.sendHeader("Location", "/");
  server.send(303);
}

void handleDetonate() {
  detonateBomb(true);
  server.sendHeader("Location", "/");
  server.send(303);
}

// -----------------------------------------------------------------------------
// Code generation
// -----------------------------------------------------------------------------
bool isValid8DigitString(const String& s) {
  if (s.length() != 8) return false;

  for (int i = 0; i < 8; i++) {
    if (s[i] < '0' || s[i] > '9') return false;
  }

  return true;
}

void generateRandomCode() {
  for (int i = 0; i < 8; i++) {
    activeCode[i] = char('0' + random(0, 10));
  }
  activeCode[8] = '\0';
}

void loadActiveCode() {
  if (settings.useRandomCode) {
    generateRandomCode();
  } else {
    strncpy(activeCode, settings.presetCode, sizeof(activeCode));
    activeCode[8] = '\0';
  }
}

// -----------------------------------------------------------------------------
// Game control
// -----------------------------------------------------------------------------
void resetEntry() {
  entryIndex = 0;
}

void resetToIdle() {
  gameState = STATE_IDLE;
  resetEntry();
  loadActiveCode();

  digitalWrite(relayPin, LOW);
  digitalWrite(redLedPin, LOW);
  digitalWrite(buzzerPin, LOW);

  relayActive = false;
  ledState = false;

  countdownStartMs = 0;
  relayStartMs = 0;
  lastBlinkMs = 0;
  lastBeepMs = 0;

  lcd.clear();
  showIdleScreen();
  sendStatus();
}

void activateForArming() {
  gameState = STATE_READY_TO_ARM;
  resetEntry();

  digitalWrite(redLedPin, LOW);
  digitalWrite(buzzerPin, LOW);

  lcd.clear();
  showReadyScreen();
}

void armBomb(bool fromRemote) {
  gameState = STATE_ARMED;
  resetEntry();

  countdownStartMs = millis();
  lastBlinkMs = 0;
  lastBeepMs = 0;
  ledState = false;

  lcd.clear();
  shortBeep(80);

  if (fromRemote) {
    sendFrame("ARMED", String(settings.timerSeconds), aojGenerateMessageId());
  }

  sendStatus();
}

void defuseBomb(bool fromRemote) {
  gameState = STATE_DEFUSED;

  digitalWrite(redLedPin, LOW);
  digitalWrite(buzzerPin, LOW);
  digitalWrite(relayPin, LOW);

  relayActive = false;

  lcd.clear();
  showDefusedScreen();

  shortBeep(50);
  delay(70);
  shortBeep(50);

  sendFrame("DEFUSED", fromRemote ? "REMOTE" : "LOCAL", aojGenerateMessageId());
  sendStatus();
}

void detonateBomb(bool fromRemote) {
  gameState = STATE_EXPLODED;

  digitalWrite(redLedPin, LOW);
  digitalWrite(relayPin, HIGH);
  digitalWrite(buzzerPin, HIGH);

  relayActive = true;
  relayStartMs = millis();

  lcd.clear();
  showExplodedScreen();

  sendFrame("EXPLODED", fromRemote ? "REMOTE" : "LOCAL", aojGenerateMessageId());
  sendStatus();
}

// -----------------------------------------------------------------------------
// Input handling
// -----------------------------------------------------------------------------
void handleReadyInput() {
  char key = keypad.getKey();

  if (!key) {
    if (millis() - lastScreenMs >= 200) {
      showReadyScreen();
      lastScreenMs = millis();
    }
    return;
  }

  if (entryIndex < 8) {
    if (key == activeCode[entryIndex]) {
      entryIndex++;
      shortBeep(25);
      showReadyScreen();
    } else if (key >= '0' && key <= '9') {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(" CODE ERROR     ");
      lcd.setCursor(0, 1);
      lcd.print("  TRY AGAIN     ");
      shortBeep(180);
      delay(700);
      resetEntry();
      showReadyScreen();
    }
  } else {
    if (key == '#') {
      armBomb(false);
    } else if (key >= '0' && key <= '9') {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(" PRESS #        ");
      lcd.setCursor(0, 1);
      lcd.print(" TO ARM         ");
      delay(450);
      showReadyScreen();
    }
  }
}

void handleArmedInput() {
  char key = keypad.getKey();

  if (!key) return;

  if (entryIndex < 8) {
    if (key == activeCode[entryIndex]) {
      entryIndex++;
      shortBeep(20);
    } else if (key >= '0' && key <= '9') {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(" DEFUSE FAIL    ");
      lcd.setCursor(0, 1);
      lcd.print(" RESTART ENTRY  ");
      shortBeep(150);
      delay(500);
      resetEntry();
    }
  } else {
    if (key == '#') {
      defuseBomb(false);
      return;
    } else if (key >= '0' && key <= '9') {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(" PRESS #        ");
      lcd.setCursor(0, 1);
      lcd.print(" TO DEFUSE      ");
      delay(350);
    }
  }
}

// -----------------------------------------------------------------------------
// Countdown / effects
// -----------------------------------------------------------------------------
void updateCountdown() {
  unsigned long elapsedMs = millis() - countdownStartMs;
  unsigned long totalMs = settings.timerSeconds * 1000UL;

  if (elapsedMs >= totalMs) {
    detonateBomb(false);
    return;
  }

  unsigned long remainingMs = totalMs - elapsedMs;

  if (millis() - lastScreenMs >= 120) {
    showArmedScreen(remainingMs);
    lastScreenMs = millis();
  }

  updateArmedEffects(remainingMs);
}

void updateArmedEffects(unsigned long remainingMs) {
  unsigned long beepInterval = 1000;
  unsigned long flashInterval = 500;

  if (remainingMs <= 30000) {
    beepInterval = 700;
    flashInterval = 350;
  }
  if (remainingMs <= 15000) {
    beepInterval = 400;
    flashInterval = 200;
  }
  if (remainingMs <= 5000) {
    beepInterval = 180;
    flashInterval = 100;
  }

  if (millis() - lastBeepMs >= beepInterval) {
    digitalWrite(buzzerPin, HIGH);
    delay(20);
    digitalWrite(buzzerPin, LOW);
    lastBeepMs = millis();
  }

  if (millis() - lastBlinkMs >= flashInterval) {
    ledState = !ledState;
    digitalWrite(redLedPin, ledState ? HIGH : LOW);
    lastBlinkMs = millis();
  }
}

void shortBeep(unsigned int durationMs) {
  digitalWrite(buzzerPin, HIGH);
  delay(durationMs);
  digitalWrite(buzzerPin, LOW);
}

// -----------------------------------------------------------------------------
// LCD
// -----------------------------------------------------------------------------
void showIdleScreen() {
  lcd.setCursor(0, 0);
  lcd.print(" FLIP SWITCH    ");
  lcd.setCursor(0, 1);
  lcd.print(" TO ACTIVATE    ");
}

void showReadyScreen() {
  lcd.setCursor(0, 0);
  lcd.print(" ENTER CODE     ");
  renderMaskedCode();
}

void showArmedScreen(unsigned long remainingMs) {
  unsigned long totalSeconds = remainingMs / 1000UL;
  unsigned int minutes = totalSeconds / 60;
  unsigned int seconds = totalSeconds % 60;

  char line0[17];
  snprintf(line0, sizeof(line0), " TIME %02u:%02u    ", minutes, seconds);

  lcd.setCursor(0, 0);
  lcd.print(line0);
  renderMaskedCode();
}

void showDefusedScreen() {
  lcd.setCursor(0, 0);
  lcd.print(" DEVICE DEFUSED ");
  lcd.setCursor(0, 1);
  lcd.print("                ");
}

void showExplodedScreen() {
  lcd.setCursor(0, 0);
  lcd.print("   DETONATED    ");
  lcd.setCursor(0, 1);
  lcd.print(" RELAY ACTIVE   ");
}

void renderMaskedCode() {
  char line[17];
  for (int i = 0; i < 16; i++) line[i] = ' ';
  line[16] = '\0';

  char codeDisplay[9];
  for (int i = 0; i < 8; i++) {
    if (i == entryIndex && entryIndex < 8) {
      codeDisplay[i] = activeCode[i];
    } else {
      codeDisplay[i] = '*';
    }
  }
  codeDisplay[8] = '\0';

  int startPos = 4;
  for (int i = 0; i < 8; i++) {
    line[startPos + i] = codeDisplay[i];
  }

  if (entryIndex >= 8) {
    line[12] = '#';
    line[13] = ' ';
    line[14] = 'O';
    line[15] = 'K';
  }

  lcd.setCursor(0, 1);
  lcd.print(line);
}
