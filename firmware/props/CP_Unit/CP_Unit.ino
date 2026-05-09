/*
  AOJ Checkpoint / Spawn Area System - Heltec WiFi LoRa 32 V3
  -----------------------------------------------------------
  Hardware:
    - Heltec WiFi LoRa 32 V3 / ESP32-S3 / SX1262
    - External SSD1309 2.42 inch I2C OLED, 128x64
    - 2 buttons: READY and ACTION
    - Active buzzer
    - 18650 battery pack

  Correct Heltec V3 wiring:
    SSD1309 SDA  -> GPIO17
    SSD1309 SCL  -> GPIO18
    READY button -> GPIO33 to GND
    ACTION button-> GPIO34 to GND
    Buzzer +     -> GPIO47 through transistor/driver recommended
    Buzzer -     -> GND
    Battery ADC  -> GPIO1 through voltage divider

  Reserved Heltec V3 LoRa pins:
    NSS  -> GPIO8
    DIO1 -> GPIO14
    RST  -> GPIO12
    BUSY -> GPIO13

  Do NOT use GPIO8, GPIO12, GPIO13, GPIO14 for buttons/buzzer/OLED.

  AOJ Server Integration:
    - Receives AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC frames from backend
    - Sends ACK and STATUS frames back to server via LoRa
    - AOJCP peer protocol (AOJCP|team|cmd|val) retained for unit-to-unit sync
    - Set DEVICE_ID to "CP_Unit_BT" for the Black Talon unit
      and "CP_Unit_TF" for the Task Force unit
*/

// =========================================================
// BOARD / SERVER IDENTITY — Edit before flashing each unit
// =========================================================

#define BOARD_HELTEC_V3

// Change to "CP_Unit_TF" and default localTeam to TEAM_TASK_FORCE
// in loadSettings() when flashing the second unit.
#define DEVICE_ID      "CP_Unit_BT"
// #define DEVICE_ID      "CP_Unit_TF"   // Task Force unit profile
#define PROP_TYPE      "CP_UNIT"
#define FW_VERSION     "1.0.0"

// Set to 1 and fill credentials to enable server WiFi status reports.
// The local web UI AP is always enabled regardless of this setting.
#define USE_WIFI       0
#define WIFI_STA_SSID  "YourFieldNetwork"
#define WIFI_STA_PASS  "YourPassword"
#define SERVER_URL     "http://192.168.1.100:8000"
#define PROP_TOKEN     ""

// =========================================================
// AOJ CP UNIT V8 — HELTEC V3 PINOUT FIXED
// =========================================================

// Japan LoRa testing frequency. Confirm legal field use.
#define LORA_FREQUENCY 923.0

// Local AP credentials for the web UI
#define AP_SSID     "AOJ-CP-UNIT"
#define AP_PASSWORD "aojcheckpoint"

// =========================================================
// INCLUDES
// =========================================================

#include <AOJ_Core.h>   // LoRa radio, comms helpers — must come first
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Preferences.h>

// =========================================================
// CORRECT HELTEC WIFI LORA 32 V3 PINOUT
// =========================================================

#define READY_BUTTON_PIN   33
#define ACTION_BUTTON_PIN  34
#define BUZZER_PIN         47
#define BATTERY_PIN        1

#define OLED_SDA 20
#define OLED_SCL 19

// Internal / board LEDs — kept LOW only to avoid current draw
#define LED_PIN_1          35
#define LED_PIN_2          36

// LoRa pins (reference only — owned by AOJ_BoardConfig.h for BOARD_HELTEC_V3):
//   LORA_NSS=8  LORA_DIO1=14  LORA_RST=12  LORA_BUSY=13

// =========================================================
// OBJECTS
// =========================================================

AojLoRa lora;

// SSD1309 2.42 inch I2C OLED
U8G2_SSD1309_128X64_NONAME0_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

WebServer server(80);
Preferences prefs;

#if defined(USE_WIFI) && USE_WIFI == 1
AojWiFi aojWifi;
#endif

// =========================================================
// ENUMS
// =========================================================

enum Team {
  TEAM_BLACK_TALON = 0,
  TEAM_TASK_FORCE  = 1
};

enum GameMode {
  MODE_DEATHMATCH_COUNTER = 0,
  MODE_KILL_LIMIT         = 1,
  MODE_RESPAWN_LIMIT      = 2,
  MODE_FLAG_CAPTURE       = 3
};

enum GameState {
  STATE_IDLE      = 0,
  STATE_READY     = 1,
  STATE_COUNTDOWN = 2,
  STATE_RUNNING   = 3,
  STATE_GAMEOVER  = 4
};

// =========================================================
// GLOBAL STATE
// =========================================================

Team      localTeam = TEAM_BLACK_TALON;
GameMode  gameMode  = MODE_DEATHMATCH_COUNTER;
GameState gameState = STATE_IDLE;

bool blackTalonReady = false;
bool taskForceReady  = false;

int blackTalonCount = 0;
int taskForceCount  = 0;

int limitValue          = 20;
int countdownSeconds    = 10;
int respawnDelaySeconds = 5;

bool   pendingLoraSync   = false;
String pendingSyncMessage = "";

// Set true when the server sends DISARM/DISABLE; cleared on RESET/ARM
bool serverAdminDisabled = false;

unsigned long countdownStartMs       = 0;
unsigned long lastStatusSendMs       = 0;
unsigned long lastServerHeartbeatMs  = 0;
unsigned long lastDisplayUpdateMs    = 0;
unsigned long lastLoraSeenMs         = 0;
unsigned long lastWifiClientSeenMs   = 0;

String lastMessage   = "BOOT";
String gameOverReason = "";

float lastRssi = 0;
float lastSnr  = 0;

// =========================================================
// FORWARD DECLARATIONS
// =========================================================

void sendLora(String command, String value);
void sendServerFrame(const String &command, const String &value);
void sendServerFrameTo(const char *targetDeviceId, const String &command, const String &value);
void signalGmUnitGameStart();
void signalGmUnitGameEnd(const String &reason);
void sendAck(const String &messageId);
void sendStatus();
void handleServerCommand(const AOJFrame &frame);
void saveSettings();
void applyModeString(String selectedMode, bool broadcast);
void applySyncMessage(String message);
void resetGame(bool broadcast);
void drawDisplay();
void buzzPatternGameOver();

// =========================================================
// BASIC HELPERS
// =========================================================

String getTeamName(Team team) {
  if (team == TEAM_BLACK_TALON) return "BLACK TALON";
  return "TASK FORCE";
}

String getShortTeamName(Team team) {
  if (team == TEAM_BLACK_TALON) return "BT";
  return "TF";
}

String getGameModeName(GameMode mode) {
  switch (mode) {
    case MODE_DEATHMATCH_COUNTER: return "DEATHMATCH COUNTER";
    case MODE_KILL_LIMIT:         return "KILL LIMIT";
    case MODE_RESPAWN_LIMIT:      return "LIMITED RESPAWNS";
    case MODE_FLAG_CAPTURE:       return "FLAG CAPTURE";
  }
  return "UNKNOWN";
}

String getGameModeValue(GameMode mode) {
  switch (mode) {
    case MODE_DEATHMATCH_COUNTER: return "deathmatch";
    case MODE_KILL_LIMIT:         return "killlimit";
    case MODE_RESPAWN_LIMIT:      return "respawnlimit";
    case MODE_FLAG_CAPTURE:       return "flag";
  }
  return "deathmatch";
}

String getGameStateName(GameState state) {
  switch (state) {
    case STATE_IDLE:      return "IDLE";
    case STATE_READY:     return "READY";
    case STATE_COUNTDOWN: return "COUNTDOWN";
    case STATE_RUNNING:   return "RUNNING";
    case STATE_GAMEOVER:  return "GAME OVER";
  }
  return "UNKNOWN";
}

// State string used in server STATUS frames
String getServerStateString() {
  if (serverAdminDisabled) return "disarmed";
  switch (gameState) {
    case STATE_IDLE:      return "idle";
    case STATE_READY:     return "ready";
    case STATE_COUNTDOWN: return "countdown";
    case STATE_RUNNING:   return "running";
    case STATE_GAMEOVER:  return "gameover";
  }
  return "idle";
}

String checkedIf(GameMode mode) {
  return gameMode == mode ? " checked" : "";
}

String checkedTeamIf(Team team) {
  return localTeam == team ? " checked" : "";
}

void forceLedsOff() {
  digitalWrite(LED_PIN_1, LOW);
  digitalWrite(LED_PIN_2, LOW);
}

void buzz(int durationMs) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(durationMs);
  digitalWrite(BUZZER_PIN, LOW);
}

void beepShort() {
  buzz(80);
}

void buzzPatternGameOver() {
  for (int i = 0; i < 3; i++) {
    buzz(250);
    delay(120);
  }
}

int readBatteryPercent() {
  int raw     = analogRead(BATTERY_PIN);
  int percent = map(raw, 2300, 3300, 0, 100);
  if (percent < 0)   percent = 0;
  if (percent > 100) percent = 100;
  return percent;
}

// =========================================================
// SETTINGS STORAGE
// =========================================================

void loadSettings() {
  prefs.begin("aojcp", false);

  localTeam           = (Team)prefs.getUInt("team", (uint32_t)TEAM_BLACK_TALON);
  gameMode            = (GameMode)prefs.getUInt("mode", (uint32_t)MODE_DEATHMATCH_COUNTER);
  limitValue          = prefs.getInt("limit", 20);
  countdownSeconds    = prefs.getInt("countdown", 10);
  respawnDelaySeconds = prefs.getInt("respawn", 5);

  prefs.end();
}

void saveSettings() {
  prefs.begin("aojcp", false);

  prefs.putUInt("team", (uint32_t)localTeam);
  prefs.putUInt("mode", (uint32_t)gameMode);
  prefs.putInt("limit",     limitValue);
  prefs.putInt("countdown", countdownSeconds);
  prefs.putInt("respawn",   respawnDelaySeconds);

  prefs.end();
}

// =========================================================
// GAME CONTROL
// =========================================================

void resetGame(bool broadcast) {
  blackTalonReady      = false;
  taskForceReady       = false;
  blackTalonCount      = 0;
  taskForceCount       = 0;
  gameOverReason       = "";
  gameState            = STATE_IDLE;
  serverAdminDisabled  = false;
  lastMessage          = "RESET";

  if (broadcast) {
    sendLora("RESET", "GAME");
  }
}

void setGameOver(String reason, bool broadcast) {
  gameState     = STATE_GAMEOVER;
  gameOverReason = reason;
  lastMessage   = "GAMEOVER " + reason;

  buzzPatternGameOver();
  signalGmUnitGameEnd(reason);

  if (broadcast) {
    sendLora("GAMEOVER", reason);
  }
}

void markReady(Team team, bool broadcast) {
  if (team == TEAM_BLACK_TALON) blackTalonReady = true;
  if (team == TEAM_TASK_FORCE)  taskForceReady  = true;

  gameState   = STATE_READY;
  lastMessage = getTeamName(team) + " READY";
  beepShort();

  if (broadcast) {
    sendLora("READY", String((int)team));
  }

  if (blackTalonReady && taskForceReady) {
    gameState        = STATE_COUNTDOWN;
    countdownStartMs = millis();

    if (broadcast) {
      sendLora("COUNTDOWN", String(countdownSeconds));
    }
  }
}

void startGame(bool broadcast) {
  if (serverAdminDisabled) return;

  gameState   = STATE_RUNNING;
  lastMessage = "GAME START";
  buzz(300);
  signalGmUnitGameStart();

  if (broadcast) {
    sendLora("START", "GAME");
  }
}

void applyModeString(String selectedMode, bool broadcast) {
  if      (selectedMode == "deathmatch")  gameMode = MODE_DEATHMATCH_COUNTER;
  else if (selectedMode == "killlimit")   gameMode = MODE_KILL_LIMIT;
  else if (selectedMode == "respawnlimit") gameMode = MODE_RESPAWN_LIMIT;
  else if (selectedMode == "flag")        gameMode = MODE_FLAG_CAPTURE;
  else                                    gameMode = MODE_DEATHMATCH_COUNTER;

  saveSettings();
  lastMessage = "MODE " + getGameModeName(gameMode);

  if (broadcast) {
    pendingLoraSync   = true;
    pendingSyncMessage = "MODE:" + selectedMode
                       + ";LIMIT:" + String(limitValue)
                       + ";COUNTDOWN:" + String(countdownSeconds)
                       + ";RESPAWN:" + String(respawnDelaySeconds);
  }
}

void registerActionPress() {
  if (serverAdminDisabled) return;
  if (gameState != STATE_RUNNING) return;

  if (localTeam == TEAM_BLACK_TALON) {
    blackTalonCount++;
    sendLora("COUNT", "BT:" + String(blackTalonCount));
  } else {
    taskForceCount++;
    sendLora("COUNT", "TF:" + String(taskForceCount));
  }

  beepShort();

  if (gameMode == MODE_KILL_LIMIT) {
    if (blackTalonCount >= limitValue)
      setGameOver("BLACK TALON HIT KILL LIMIT", true);
    if (taskForceCount >= limitValue)
      setGameOver("TASK FORCE HIT KILL LIMIT", true);
  }

  if (gameMode == MODE_RESPAWN_LIMIT) {
    if (blackTalonCount >= limitValue)
      setGameOver("BLACK TALON RESPAWNS EXHAUSTED", true);
    if (taskForceCount >= limitValue)
      setGameOver("TASK FORCE RESPAWNS EXHAUSTED", true);
  }
}

void captureFlag() {
  if (serverAdminDisabled) return;
  if (gameState != STATE_RUNNING) return;
  setGameOver("FLAG CAPTURED BY " + getTeamName(localTeam), true);
}

// =========================================================
// SERVER FRAME HELPERS  (AOJ|DEVICE_ID|CMD|VAL|MID|CRC)
// =========================================================

void sendServerFrame(const String &command, const String &value) {
  String msgId = aojGenerateMessageId();
  String frame = aojBuildFrame(DEVICE_ID, command, value, msgId);
  lora.send(frame);
}

void sendServerFrameTo(const char *targetDeviceId, const String &command, const String &value) {
  String msgId = aojGenerateMessageId();
  String frame = aojBuildFrame(targetDeviceId, command, value, msgId);
  lora.send(frame);
}

void signalGmUnitGameStart() {
  sendServerFrameTo("GM_Unit", "GAME_START", DEVICE_ID);
}

void signalGmUnitGameEnd(const String &reason) {
  sendServerFrameTo("GM_Unit", "GAME_END", reason);
}

void sendAck(const String &messageId) {
  String frame = aojBuildFrame(DEVICE_ID, "ACK", "OK", messageId);
  lora.send(frame);
}

void sendStatus() {
  String payload = String("state=") + getServerStateString()
                 + ",mode="    + getGameModeValue(gameMode)
                 + ",bt="      + String(blackTalonCount)
                 + ",tf="      + String(taskForceCount)
                 + ",limit="   + String(limitValue)
                 + ",bat="     + String(readBatteryPercent())
                 + ",fw="      + FW_VERSION;
  sendServerFrame("STATUS", payload);
}

// Map an incoming AOJ server command to local game actions.
// ACK is already sent by receiveLora() before this is called.
void handleServerCommand(const AOJFrame &frame) {
  const String &cmd = frame.command;
  const String &val = frame.value;

  lastMessage = "SRV " + cmd;

  if (cmd == "STATUS_REQUEST") {
    sendStatus();

  } else if (cmd == "RESET") {
    resetGame(true);

  } else if (cmd == "ARM" || cmd == "ENABLE") {
    serverAdminDisabled = false;
    lastMessage = "ARMED";
    beepShort();

  } else if (cmd == "DISARM" || cmd == "DISABLE") {
    serverAdminDisabled = true;
    gameState = STATE_IDLE;
    blackTalonReady = false;
    taskForceReady = false;
    lastMessage = "DISARMED";
    beepShort();

  } else if (cmd == "TRIGGER_ALARM" || cmd == "GAMEOVER" || cmd == "GAME_END") {
    setGameOver("SERVER: " + (val.length() > 0 ? val : cmd), false);

  } else if (cmd == "START" || cmd == "GAME_START") {
    startGame(false);

  } else if (cmd == "READY") {
    markReady(localTeam, false);

  } else if (cmd == "SET_MODE") {
    applyModeString(val, false);

  } else if (cmd == "SET_LIMIT") {
    int v = val.toInt();
    if (v > 0) {
      limitValue = v;
      saveSettings();
      lastMessage = "LIMIT " + String(limitValue);
    }

  } else if (cmd == "SET_COUNTDOWN") {
    int v = val.toInt();
    if (v > 0) {
      countdownSeconds = v;
      saveSettings();
      lastMessage = "COUNTDOWN " + String(countdownSeconds);
    }

  } else if (cmd == "SET_TEAM") {
    if (val == "BT" || val == "BLACK_TALON") {
      localTeam = TEAM_BLACK_TALON;
    } else if (val == "TF" || val == "TASK_FORCE") {
      localTeam = TEAM_TASK_FORCE;
    }
    saveSettings();
    lastMessage = "TEAM " + getTeamName(localTeam);

  } else if (cmd == "TEST" || cmd == "BUZZ") {
    buzz(200);

  } else {
    lastMessage = "UNK " + cmd;
  }
}

// =========================================================
// LORA — Peer protocol: AOJCP|senderTeam|command|value
// =========================================================

void sendLora(String command, String value) {
  String packet = "AOJCP|" + String((int)localTeam) + "|" + command + "|" + value;
  lora.send(packet);
  forceLedsOff();
}

void applySyncMessage(String message) {
  int start = 0;

  while (start < (int)message.length()) {
    int end  = message.indexOf(';', start);
    if (end == -1) end = message.length();

    String part = message.substring(start, end);
    int    sep  = part.indexOf(':');

    if (sep > 0) {
      String key   = part.substring(0, sep);
      String value = part.substring(sep + 1);

      if (key == "MODE")      applyModeString(value, false);
      if (key == "LIMIT")     limitValue          = value.toInt();
      if (key == "COUNTDOWN") countdownSeconds    = value.toInt();
      if (key == "RESPAWN")   respawnDelaySeconds = value.toInt();
    }

    start = end + 1;
  }

  saveSettings();
  lastMessage = "SETTINGS SYNCED";
  beepShort();
}

void handlePacket(const String &packet) {
  if (!packet.startsWith("AOJCP|")) return;

  int p1 = packet.indexOf('|');
  int p2 = packet.indexOf('|', p1 + 1);
  int p3 = packet.indexOf('|', p2 + 1);

  if (p1 < 0 || p2 < 0 || p3 < 0) return;

  int    senderTeam = packet.substring(p1 + 1, p2).toInt();
  String command    = packet.substring(p2 + 1, p3);
  String value      = packet.substring(p3 + 1);

  // Ignore own packets
  if (senderTeam == (int)localTeam) return;

  lastLoraSeenMs = millis();
  lastRssi = (float)lora.rssiRaw();
  lastSnr  = 0;
  lastMessage = command + " " + value;

  if      (command == "READY")    { markReady((Team)value.toInt(), false); }
  else if (command == "COUNTDOWN") {
    countdownSeconds = value.toInt();
    gameState        = STATE_COUNTDOWN;
    countdownStartMs = millis();
  }
  else if (command == "START")    { startGame(false); }
  else if (command == "RESET")    { resetGame(false); }
  else if (command == "GAMEOVER") { setGameOver(value, false); }
  else if (command == "COUNT") {
    if (value.startsWith("BT:")) blackTalonCount = value.substring(3).toInt();
    if (value.startsWith("TF:")) taskForceCount  = value.substring(3).toInt();
  }
  else if (command == "PING")     { sendLora("PONG", getTeamName(localTeam)); }
  else if (command == "PONG")     { lastMessage = "LORA LINK CONFIRMED"; }
  else if (command == "BUZZ")     { buzz(200); }
  else if (command == "SYNC")     { applySyncMessage(value); }
  else if (command == "MODE")     { applyModeString(value, false); }

  forceLedsOff();
}

// Non-blocking interrupt-driven receive.
// Routes AOJ server frames first, then AOJCP peer packets.
void receiveLora() {
  if (!lora.available()) return;

  String received = lora.read();
  if (received.length() == 0) return;

  // AOJ server frame: AOJ|DEVICE_ID|CMD|VAL|MID|CRC
  if (received.startsWith("AOJ|")) {
    AOJFrame frame = aojParseFrame(received);
    if (frame.valid) {
      // Ignore commands not addressed to this unit.
      if (frame.deviceId != DEVICE_ID && frame.deviceId != "*") {
        forceLedsOff();
        return;
      }

      // ACK immediately so the server stops retrying
      sendAck(frame.messageId);
      handleServerCommand(frame);
      lastLoraSeenMs = millis();
      lastRssi = (float)lora.rssiRaw();
      lastSnr  = 0;
    }
    forceLedsOff();
    return;
  }

  // AOJCP peer packet: AOJCP|team|cmd|val
  handlePacket(received);
  forceLedsOff();
}

// =========================================================
// DISPLAY
// =========================================================

void drawSignalBars(int x, int y, int bars) {
  for (int i = 0; i < 4; i++) {
    int height = (i + 1) * 3;
    int bx = x + (i * 4);
    int by = y - height;

    if (i < bars) {
      display.drawBox(bx, by, 3, height);
    } else {
      display.drawFrame(bx, by, 3, height);
    }
  }
}

void drawDisplay() {
  display.clearBuffer();
  display.setFont(u8g2_font_6x12_tf);

  display.drawFrame(0, 0, 128, 64);
  display.drawStr(3, 10, "AOJ CP UNIT");

  int wifiBars = WiFi.softAPgetStationNum() > 0 ? 4 : 1;
  int loraBars = (millis() - lastLoraSeenMs < 15000) ? 4 : 1;

  display.drawStr(84, 10, "W");
  drawSignalBars(92, 10, wifiBars);
  display.drawStr(105, 10, "L");
  drawSignalBars(113, 10, loraBars);

  display.drawLine(0, 14, 128, 14);

  display.drawStr(4, 26, getShortTeamName(localTeam).c_str());
  display.drawStr(24, 26, getGameStateName(gameState).c_str());

  String modeLine = getGameModeName(gameMode);
  if (modeLine.length() > 20) modeLine = modeLine.substring(0, 20);
  display.drawStr(4, 38, modeLine.c_str());

  String counts = "BT:" + String(blackTalonCount)
                + " TF:" + String(taskForceCount)
                + " L:" + String(limitValue);
  display.drawStr(4, 50, counts.c_str());

  if (serverAdminDisabled) {
    display.drawStr(4, 62, "DISARMED BY SERVER");
  } else if (gameState == STATE_GAMEOVER) {
    display.drawStr(4, 62, "ADMIN RESET REQUIRED");
  } else if (gameState == STATE_COUNTDOWN) {
    int remain = countdownSeconds - (int)((millis() - countdownStartMs) / 1000);
    if (remain < 0) remain = 0;
    String cd = "START IN " + String(remain);
    display.drawStr(4, 62, cd.c_str());
  } else {
    String batt = "BAT " + String(readBatteryPercent()) + "%";
    display.drawStr(4, 62, batt.c_str());
  }

  display.sendBuffer();
}

// =========================================================
// BUTTONS
// =========================================================

bool isButtonPressed(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

void handleReadyButton() {
  static bool wasPressed = false;
  bool nowPressed = isButtonPressed(READY_BUTTON_PIN);

  if (serverAdminDisabled) {
    wasPressed = nowPressed;
    return;
  }

  if (nowPressed && !wasPressed) {
    markReady(localTeam, true);
  }

  wasPressed = nowPressed;
}

void handleActionButton() {
  static bool wasPressed    = false;
  static unsigned long pressStartMs = 0;
  static bool flagCaptured  = false;

  bool nowPressed = isButtonPressed(ACTION_BUTTON_PIN);

  if (serverAdminDisabled) {
    wasPressed = nowPressed;
    return;
  }

  if (nowPressed && !wasPressed) {
    pressStartMs  = millis();
    flagCaptured  = false;
  }

  if (nowPressed && !flagCaptured
      && gameMode == MODE_FLAG_CAPTURE
      && millis() - pressStartMs >= 3000) {
    flagCaptured = true;
    captureFlag();
  }

  if (!nowPressed && wasPressed) {
    unsigned long heldMs = millis() - pressStartMs;

    if (heldMs < 3000 && gameMode != MODE_FLAG_CAPTURE) {
      registerActionPress();
    }
  }

  wasPressed = nowPressed;
}

// =========================================================
// WEB UI
// =========================================================

String css() {
  return R"rawliteral(
<style>
body{
  margin:0;
  font-family:Arial,Helvetica,sans-serif;
  background:#050505;
  color:#ddd;
  background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
  background-size:22px 22px;
}
.wrap{max-width:760px;margin:auto;padding:18px;}
.brand{color:#d71920;font-size:24px;font-weight:900;letter-spacing:1px;white-space:nowrap;text-transform:uppercase;}
.title{font-size:40px;font-weight:900;color:white;margin:6px 0 18px 0;letter-spacing:3px;}
.panel{background:#0b0b0b;border:1px solid #2a2a2a;margin:14px 0;padding:14px;box-shadow:0 0 14px rgba(215,25,32,.16);}
h2{font-size:16px;color:#fff;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:8px;}
.row{display:flex;gap:10px;flex-wrap:wrap;}
.stat{background:#121212;border:1px solid #333;padding:10px;flex:1;min-width:135px;}
.label{color:#999;font-size:11px;text-transform:uppercase;}
.value{color:#fff;font-size:18px;font-weight:800;margin-top:4px;}
.red{color:#d71920;}
.blue{color:#4aa3ff;}
button{background:#d71920;color:white;border:0;padding:13px 16px;margin:5px 4px 5px 0;font-weight:900;border-radius:3px;letter-spacing:.5px;}
button.secondary{background:#222;border:1px solid #555;}
button.warn{background:#ff9d00;color:#111;}
button.dark{background:#111;border:1px solid #666;}
input[type=number]{background:#111;color:white;border:1px solid #555;padding:12px;width:110px;font-size:16px;}
.mode-option{display:block;background:#121212;border:1px solid #333;margin:8px 0;padding:12px;font-weight:800;}
.mode-option input{transform:scale(1.35);margin-right:10px;}
a{color:white;text-decoration:none;}
.small{font-size:12px;color:#aaa;}
.gameover{border:2px solid #d71920;background:#180506;}
</style>
)rawliteral";
}

String htmlPage() {
  String page = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  page += css();
  page += "</head><body><div class='wrap'>";

  page += "<div class='brand'>Airsoft Online Japan</div>";
  page += "<div class='title'>CP UNIT</div>";

  if (serverAdminDisabled) {
    page += "<div class='panel' style='border-color:#ff9d00'><h2>DISARMED BY SERVER</h2>";
    page += "<p class='small'>This unit has been remotely disabled. Waiting for server ARM command.</p></div>";
  }

  if (gameState == STATE_GAMEOVER) {
    page += "<div class='panel gameover'><h2>GAME OVER</h2>";
    page += "<div class='value red'>" + gameOverReason + "</div>";
    page += "<p class='small'>Admin reset required before next game.</p></div>";
  }

  page += "<div class='panel'><h2>Status</h2><div class='row'>";
  page += "<div class='stat'><div class='label'>Unit</div><div class='value'>" + getTeamName(localTeam) + "</div></div>";
  page += "<div class='stat'><div class='label'>State</div><div class='value'>" + getGameStateName(gameState) + "</div></div>";
  page += "<div class='stat'><div class='label'>Mode</div><div class='value'>" + getGameModeName(gameMode) + "</div></div>";
  page += "<div class='stat'><div class='label'>Battery</div><div class='value'>" + String(readBatteryPercent()) + "%</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Game Results</h2><div class='row'>";
  page += "<div class='stat'><div class='label red'>Black Talon</div><div class='value'>" + String(blackTalonCount) + "</div></div>";
  page += "<div class='stat'><div class='label blue'>Task Force</div><div class='value'>" + String(taskForceCount) + "</div></div>";
  page += "<div class='stat'><div class='label'>Limit</div><div class='value'>" + String(limitValue) + "</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Game Mode</h2>";
  page += "<form action='/setmode' method='GET'>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='deathmatch'" + checkedIf(MODE_DEATHMATCH_COUNTER) + "> Deathmatch Counter</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='killlimit'" + checkedIf(MODE_KILL_LIMIT) + "> Kill Limit</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='respawnlimit'" + checkedIf(MODE_RESPAWN_LIMIT) + "> Limited Respawns</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='flag'" + checkedIf(MODE_FLAG_CAPTURE) + "> Flag Capture</label>";
  page += "<button type='submit'>ACTIVATE MODE</button>";
  page += "</form>";
  page += "<p class='small'>Mode applies locally first, then syncs to the second CP unit by LoRa.</p>";
  page += "</div>";

  page += "<div class='panel'><h2>Team Assignment</h2>";
  page += "<form action='/setteam' method='GET'>";
  page += "<label class='mode-option'><input type='radio' name='team' value='BT'" + checkedTeamIf(TEAM_BLACK_TALON) + "> Black Talon</label>";
  page += "<label class='mode-option'><input type='radio' name='team' value='TF'" + checkedTeamIf(TEAM_TASK_FORCE) + "> Task Force</label>";
  page += "<button type='submit'>SAVE TEAM</button>";
  page += "</form>";
  page += "<p class='small'>Set this unit's local team for scoring and ready/action behavior.</p>";
  page += "</div>";

  page += "<div class='panel'><h2>Spawn / Limit Settings</h2>";
  page += "<form action='/settings' method='GET'>";
  page += "<p>Kill / Respawn Limit<br><input type='number' name='limit' value='" + String(limitValue) + "'></p>";
  page += "<p>Countdown Seconds<br><input type='number' name='countdown' value='" + String(countdownSeconds) + "'></p>";
  page += "<p>Respawn Delay Seconds<br><input type='number' name='respawn' value='" + String(respawnDelaySeconds) + "'></p>";
  page += "<button type='submit'>SAVE AND SYNC SETTINGS</button>";
  page += "</form></div>";

  page += "<div class='panel'><h2>Admin Controls</h2>";
  page += "<a href='/ready'><button class='secondary'>FORCE READY</button></a>";
  page += "<a href='/start'><button>FORCE START</button></a>";
  page += "<a href='/gameover'><button class='warn'>END GAME</button></a>";
  page += "<a href='/reset'><button class='dark'>RESET FOR NEXT GAME</button></a>";
  page += "</div>";

  page += "<div class='panel'><h2>LoRa Tools</h2>";
  page += "<a href='/ping'><button class='secondary'>TEST LORA LINK</button></a>";
  page += "<a href='/beep'><button class='secondary'>REMOTE BUZZER TEST</button></a>";
  page += "<div class='small'>Last packet: " + lastMessage
       + "<br>RSSI: " + String(lastRssi) + " dBm"
       + "<br>SNR: "  + String(lastSnr)  + " dB</div>";
  page += "</div>";

  page += "<script>setTimeout(()=>{location.reload();},5000);</script>";
  page += "</div></body></html>";

  return page;
}

void redirectHome() {
  server.sendHeader("Location", "/");
  server.send(303, "text/plain", "");
}

void setupWifi() {
  WiFi.mode(WIFI_AP);
  WiFi.setSleep(false);
  WiFi.softAP(AP_SSID, AP_PASSWORD, 6, 0, 4);

  server.on("/", HTTP_GET, []() {
    if (WiFi.softAPgetStationNum() > 0) lastWifiClientSeenMs = millis();
    server.send(200, "text/html", htmlPage());
  });

  server.on("/setmode", HTTP_GET, []() {
    if (!server.hasArg("mode")) {
      server.send(400, "text/plain", "NO MODE SELECTED");
      return;
    }
    applyModeString(server.arg("mode"), true);
    redirectHome();
  });

  server.on("/setteam", HTTP_GET, []() {
    if (!server.hasArg("team")) {
      server.send(400, "text/plain", "NO TEAM SELECTED");
      return;
    }

    String team = server.arg("team");
    if (team == "BT") {
      localTeam = TEAM_BLACK_TALON;
    } else if (team == "TF") {
      localTeam = TEAM_TASK_FORCE;
    } else {
      server.send(400, "text/plain", "INVALID TEAM");
      return;
    }

    saveSettings();
    lastMessage = "TEAM " + getTeamName(localTeam);
    beepShort();
    redirectHome();
  });

  server.on("/settings", HTTP_GET, []() {
    if (server.hasArg("limit"))     limitValue          = server.arg("limit").toInt();
    if (server.hasArg("countdown")) countdownSeconds    = server.arg("countdown").toInt();
    if (server.hasArg("respawn"))   respawnDelaySeconds = server.arg("respawn").toInt();

    if (limitValue < 1)          limitValue = 1;
    if (countdownSeconds < 1)    countdownSeconds = 1;
    if (respawnDelaySeconds < 0) respawnDelaySeconds = 0;

    saveSettings();

    pendingLoraSync   = true;
    pendingSyncMessage = "MODE:" + getGameModeValue(gameMode)
                       + ";LIMIT:" + String(limitValue)
                       + ";COUNTDOWN:" + String(countdownSeconds)
                       + ";RESPAWN:" + String(respawnDelaySeconds);

    redirectHome();
  });

  server.on("/ready",    HTTP_GET, []() { markReady(localTeam, true); redirectHome(); });
  server.on("/start",    HTTP_GET, []() { startGame(true);            redirectHome(); });
  server.on("/reset",    HTTP_GET, []() { resetGame(true);            redirectHome(); });
  server.on("/gameover", HTTP_GET, []() { setGameOver("ADMIN ENDED GAME", true); redirectHome(); });

  server.on("/ping", HTTP_GET, []() {
    sendLora("PING", "TEST");
    redirectHome();
  });

  server.on("/beep", HTTP_GET, []() {
    buzz(120);
    sendLora("BUZZ", "REMOTE");
    redirectHome();
  });

  server.begin();
}

// =========================================================
// SETUP / LOOP
// =========================================================

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(READY_BUTTON_PIN, INPUT_PULLUP);
  pinMode(ACTION_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN,  OUTPUT);
  pinMode(LED_PIN_1,   OUTPUT);
  pinMode(LED_PIN_2,   OUTPUT);
  forceLedsOff();

  analogReadResolution(12);

  loadSettings();

  Wire.begin(OLED_SDA, OLED_SCL);
  display.setI2CAddress(0x3C * 2);
  display.begin();
  display.clearBuffer();
  display.setFont(u8g2_font_6x12_tf);
  display.drawStr(0, 12, "AOJ CP UNIT");
  display.drawStr(0, 28, "BOOTING...");
  display.sendBuffer();

  bool loraOk = lora.begin();
  lastMessage = loraOk ? "LORA READY" : "LORA FAIL";

  setupWifi();

#if defined(USE_WIFI) && USE_WIFI == 1
  // Switch to AP+STA so local web UI and server WiFi coexist
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID, AP_PASSWORD, 6, 0, 4);
  aojWifi.begin(WIFI_STA_SSID, WIFI_STA_PASS, SERVER_URL, PROP_TOKEN);
#endif

  sendLora("HELLO", getTeamName(localTeam));
  sendStatus();  // announce to server on boot

  buzz(120);
  forceLedsOff();
}

void loop() {
  server.handleClient();

  receiveLora();

  handleReadyButton();
  handleActionButton();

  // Countdown → game start
  if (gameState == STATE_COUNTDOWN) {
    unsigned long elapsed = (millis() - countdownStartMs) / 1000;
    if (elapsed >= (unsigned long)countdownSeconds) {
      startGame(true);
    }
  }

  // Pending peer SYNC broadcast
  if (pendingLoraSync) {
    pendingLoraSync = false;
    sendLora("SYNC", pendingSyncMessage);
  }

  // Peer status broadcast every 5 s (battery level to other CP unit)
  if (millis() - lastStatusSendMs > 5000) {
    lastStatusSendMs = millis();
    sendLora("STATUS", String(readBatteryPercent()));
  }

  // Server heartbeat every 15 s
  if (millis() - lastServerHeartbeatMs > 15000) {
    lastServerHeartbeatMs = millis();
    sendStatus();

#if defined(USE_WIFI) && USE_WIFI == 1
    aojWifi.reportStatus(DEVICE_ID, getServerStateString().c_str(),
                         readBatteryPercent(), lora.rssiPercent(), FW_VERSION);
#endif
  }

  if (millis() - lastDisplayUpdateMs > 250) {
    lastDisplayUpdateMs = millis();
    drawDisplay();
  }

  forceLedsOff();
  delay(5);
}
