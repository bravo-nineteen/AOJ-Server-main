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

// Task Force profile.
#define DEVICE_ID      "CP_Unit_TF"
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
#define AP_SSID     "AOJ-CP-UNIT_TF"
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
  MODE_FLAG_CAPTURE       = 3,
  MODE_GAME_TIME          = 4
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

Team      localTeam = TEAM_TASK_FORCE;
GameMode  gameMode  = MODE_DEATHMATCH_COUNTER;
GameState gameState = STATE_IDLE;

bool blackTalonReady = false;
bool taskForceReady  = false;

int blackTalonCount = 0;
int taskForceCount  = 0;

int limitValue          = 20;
int countdownSeconds    = 5;
int respawnDelaySeconds = 5;
int gameTimerMinutes    = 15;
bool hideOpponentScores = true;
bool adminScoreReveal   = false;
bool ctfHoldActive      = false;
bool ctfCaptureTriggered = false;
unsigned long ctfHoldStartMs = 0;
unsigned long ctfCapturedBannerUntilMs = 0;
bool countdownMaster    = false;
int lastCountdownBeepSecond = -1;
unsigned long gameStartMs = 0;
bool gameTimeExpired = false;
unsigned long gameTimeExpiredMs = 0;
unsigned long buzzerOffMs = 0;

const int GAME_START_COUNTDOWN_SECONDS = 5;
const unsigned long COUNTDOWN_SYNC_DELAY_MS = 1200;
const unsigned long DEATHMATCH_GRACE_MS = 120000;

bool   pendingLoraSync   = false;
String pendingSyncMessage = "";

// Set true when the server sends DISARM/DISABLE; cleared on RESET/ARM
bool serverAdminDisabled = false;

unsigned long countdownStartMs       = 0;
unsigned long countdownEndMs         = 0;
unsigned long lastStatusSendMs       = 0;
unsigned long lastServerHeartbeatMs  = 0;
unsigned long lastDisplayUpdateMs    = 0;
unsigned long lastLoraSeenMs         = 0;
unsigned long lastWifiClientSeenMs   = 0;
unsigned long gameStartBannerUntilMs = 0;

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
void applyCountdownSync(unsigned long syncValue);
String buildSettingsSyncMessage();
void queueSettingsSync();
void resetGame(bool broadcast);
void beginGameCountdown(bool broadcast);
bool modeUsesLimit(GameMode mode);
bool canShowOpponentScoreOnUnit();
void updateBuzzer();
void drawBootSplash();
void drawCenteredText(const String &text, int y, const uint8_t *font);
void drawHeader();
void drawCtfRunningScreen();
void drawGameOverScreen();
void drawDisplay();
void buzzPatternGameOver();
void handleAdminRevealButtons();

int getGameTimerMinutesSafe();
unsigned long getGameDurationMs();
unsigned long getElapsedGameMs();
String getReadyStatusLabel(bool ready);

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
    case MODE_GAME_TIME:          return "GAME TIME";
  }
  return "UNKNOWN";
}

String getGameModeValue(GameMode mode) {
  switch (mode) {
    case MODE_DEATHMATCH_COUNTER: return "deathmatch";
    case MODE_KILL_LIMIT:         return "killlimit";
    case MODE_RESPAWN_LIMIT:      return "respawnlimit";
    case MODE_FLAG_CAPTURE:       return "flag";
    case MODE_GAME_TIME:          return "gametime";
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

String checkedHideOpponentIf(bool hidden) {
  return hideOpponentScores == hidden ? " checked" : "";
}

bool canShowAllScores() {
  return !hideOpponentScores || adminScoreReveal;
}

bool modeUsesLimit(GameMode mode) {
  return mode == MODE_KILL_LIMIT || mode == MODE_RESPAWN_LIMIT;
}

bool canShowOpponentScoreOnUnit() {
  return !hideOpponentScores || gameState == STATE_COUNTDOWN;
}

String buildSettingsSyncMessage() {
  return "MODE:" + getGameModeValue(gameMode)
       + ";LIMIT:" + String(limitValue)
       + ";COUNTDOWN:" + String(GAME_START_COUNTDOWN_SECONDS)
       + ";RESPAWN:" + String(respawnDelaySeconds)
       + ";GAMETIMER:" + String(getGameTimerMinutesSafe())
       + ";HIDEOPP:" + String(hideOpponentScores ? 1 : 0);
}

void queueSettingsSync() {
  pendingLoraSync = true;
  pendingSyncMessage = buildSettingsSyncMessage();
}

void applyCountdownSync(unsigned long syncValue) {
  unsigned long startMs = syncValue;
  if (startMs < 5000UL) {
    startMs = millis() + syncValue;
  }

  if (startMs <= millis()) {
    startMs = millis() + COUNTDOWN_SYNC_DELAY_MS;
  }

  countdownSeconds = GAME_START_COUNTDOWN_SECONDS;
  gameState = STATE_COUNTDOWN;
  countdownStartMs = startMs;
  countdownEndMs = countdownStartMs + ((unsigned long)GAME_START_COUNTDOWN_SECONDS * 1000UL);
  lastCountdownBeepSecond = -1;
  countdownMaster = false;
}

void forceLedsOff() {
  digitalWrite(LED_PIN_1, LOW);
  digitalWrite(LED_PIN_2, LOW);
}

void buzz(int durationMs) {
  digitalWrite(BUZZER_PIN, HIGH);
  buzzerOffMs = millis() + (unsigned long)durationMs;
}

void updateBuzzer() {
  if (buzzerOffMs > 0 && millis() >= buzzerOffMs) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerOffMs = 0;
  }
}

void beepShort() {
  buzz(80);
}

void buzzPatternGameOver() {
  buzz(1200);
}

int readBatteryPercent() {
  int raw     = analogRead(BATTERY_PIN);
  int percent = map(raw, 2300, 3300, 0, 100);
  if (percent < 0)   percent = 0;
  if (percent > 100) percent = 100;
  return percent;
}

int getGameTimerMinutesSafe() {
  if (gameTimerMinutes < 1) return 1;
  if (gameTimerMinutes > 180) return 180;
  return gameTimerMinutes;
}

unsigned long getGameDurationMs() {
  return (unsigned long)getGameTimerMinutesSafe() * 60000UL;
}

unsigned long getElapsedGameMs() {
  if (gameStartMs == 0) return 0;
  return millis() - gameStartMs;
}

String getReadyStatusLabel(bool ready) {
  return ready ? "READY" : "WAIT";
}

// =========================================================
// SETTINGS STORAGE
// =========================================================

void loadSettings() {
  prefs.begin("aojcp", false);

  localTeam           = (Team)prefs.getUInt("team", (uint32_t)TEAM_TASK_FORCE);
  gameMode            = (GameMode)prefs.getUInt("mode", (uint32_t)MODE_DEATHMATCH_COUNTER);
  limitValue          = prefs.getInt("limit", 20);
  countdownSeconds    = GAME_START_COUNTDOWN_SECONDS;
  respawnDelaySeconds = prefs.getInt("respawn", 5);
  gameTimerMinutes    = prefs.getInt("gametimer", 15);
  hideOpponentScores  = prefs.getBool("hideopp", true);

  prefs.end();
}

void saveSettings() {
  prefs.begin("aojcp", false);

  prefs.putUInt("team", (uint32_t)localTeam);
  prefs.putUInt("mode", (uint32_t)gameMode);
  prefs.putInt("limit",     limitValue);
  prefs.putInt("countdown", GAME_START_COUNTDOWN_SECONDS);
  prefs.putInt("respawn",   respawnDelaySeconds);
  prefs.putInt("gametimer", getGameTimerMinutesSafe());
  prefs.putBool("hideopp",  hideOpponentScores);

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
  ctfHoldActive        = false;
  ctfCaptureTriggered  = false;
  ctfHoldStartMs       = 0;
  ctfCapturedBannerUntilMs = 0;
  lastCountdownBeepSecond = -1;
  countdownMaster      = false;
  gameStartMs          = 0;
  gameTimeExpired      = false;
  gameTimeExpiredMs    = 0;
  gameStartBannerUntilMs = 0;
  countdownEndMs       = 0;
  gameState            = STATE_IDLE;
  serverAdminDisabled  = false;
  adminScoreReveal     = false;
  lastMessage          = "RESET";

  if (broadcast) {
    sendLora("RESET", "GAME");
  }
}

void setGameOver(String reason, bool broadcast) {
  gameState     = STATE_GAMEOVER;
  gameOverReason = reason;
  adminScoreReveal = false;
  ctfHoldActive  = false;
  ctfCaptureTriggered = false;
  ctfHoldStartMs = 0;
  lastMessage   = "GAMEOVER " + reason;

  buzzPatternGameOver();
  signalGmUnitGameEnd(reason);

  if (broadcast) {
    sendLora("GAMEOVER", reason);
    sendLora("FINAL", "BT:" + String(blackTalonCount)
                    + ";TF:" + String(taskForceCount)
                    + ";REASON:" + reason);
  }
}

void beginGameCountdown(bool broadcast) {
  if (serverAdminDisabled) return;
  if (gameState == STATE_RUNNING || gameState == STATE_GAMEOVER) return;

  countdownSeconds = GAME_START_COUNTDOWN_SECONDS;
  gameState = STATE_COUNTDOWN;
  countdownStartMs = millis() + COUNTDOWN_SYNC_DELAY_MS;
  countdownEndMs = countdownStartMs + ((unsigned long)GAME_START_COUNTDOWN_SECONDS * 1000UL);
  lastCountdownBeepSecond = -1;
  countdownMaster = broadcast;
  lastMessage = "COUNTDOWN SYNC";

  if (broadcast) {
    sendLora("COUNTDOWN_SYNC", String(countdownStartMs));
  }
}

void markReady(Team team, bool broadcast) {
  if (serverAdminDisabled) return;
  if (gameState == STATE_COUNTDOWN || gameState == STATE_RUNNING || gameState == STATE_GAMEOVER) return;

  if (team == TEAM_BLACK_TALON) blackTalonReady = true;
  if (team == TEAM_TASK_FORCE)  taskForceReady  = true;

  gameState   = STATE_READY;
  lastMessage = getTeamName(team) + " READY";
  beepShort();

  if (broadcast) {
    sendLora("READY", String((int)team));
  }

  if (blackTalonReady && taskForceReady) {
    beginGameCountdown(broadcast);
  }
}

void startGame(bool broadcast) {
  if (serverAdminDisabled) return;
  if (gameState == STATE_RUNNING || gameState == STATE_GAMEOVER) return;

  gameState   = STATE_RUNNING;
  adminScoreReveal = false;
  gameStartMs = millis();
  gameStartBannerUntilMs = millis() + 2000;
  gameTimeExpired = false;
  gameTimeExpiredMs = 0;
  lastMessage = "GAME START";
  buzz(1500);
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
  else if (selectedMode == "gametime")     gameMode = MODE_GAME_TIME;
  else                                    gameMode = MODE_DEATHMATCH_COUNTER;

  saveSettings();
  lastMessage = "MODE " + getGameModeName(gameMode);

  if (broadcast) {
    queueSettingsSync();
  }
}

void registerActionPress() {
  if (serverAdminDisabled) return;
  if (gameState != STATE_RUNNING) return;
  if (gameMode == MODE_GAME_TIME) return;

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
  if (gameTimeExpired) return;

  Team capturingTeam = (localTeam == TEAM_BLACK_TALON) ? TEAM_TASK_FORCE : TEAM_BLACK_TALON;
  ctfCapturedBannerUntilMs = millis() + 3000;
  setGameOver("FLAG CAPTURED BY " + getTeamName(capturingTeam), true);
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
                 + ",timer="   + String(getGameTimerMinutesSafe())
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
    beginGameCountdown(false);

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
      countdownSeconds = GAME_START_COUNTDOWN_SECONDS;
      saveSettings();
      lastMessage = "COUNTDOWN " + String(countdownSeconds);
    }

  } else if (cmd == "SET_GAME_TIMER") {
    int v = val.toInt();
    if (v >= 1 && v <= 180) {
      gameTimerMinutes = v;
      saveSettings();
      lastMessage = "TIMER " + String(getGameTimerMinutesSafe()) + "M";
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
      if (key == "COUNTDOWN") countdownSeconds    = GAME_START_COUNTDOWN_SECONDS;
      if (key == "RESPAWN")   respawnDelaySeconds = value.toInt();
      if (key == "GAMETIMER") gameTimerMinutes    = value.toInt();
      if (key == "HIDEOPP")   hideOpponentScores  = (value == "1");
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
  else if (command == "COUNTDOWN" || command == "COUNTDOWN_SYNC") {
    applyCountdownSync(value.toInt());
  }
  else if (command == "START")    { startGame(false); }
  else if (command == "RESET")    { resetGame(false); }
  else if (command == "GAMEOVER") { setGameOver(value, false); }
  else if (command == "FINAL") {
    int btPos = value.indexOf("BT:");
    int tfPos = value.indexOf(";TF:");
    int rsPos = value.indexOf(";REASON:");
    if (btPos == 0 && tfPos > btPos && rsPos > tfPos) {
      blackTalonCount = value.substring(3, tfPos).toInt();
      taskForceCount  = value.substring(tfPos + 4, rsPos).toInt();
      String reason   = value.substring(rsPos + 8);
      gameOverReason  = reason;
      gameState       = STATE_GAMEOVER;
      ctfCapturedBannerUntilMs = millis();
      adminScoreReveal = false;
      lastMessage     = "FINAL SYNC";
    }
  }
  else if (command == "COUNT") {
    if (value.startsWith("BT:")) blackTalonCount = value.substring(3).toInt();
    if (value.startsWith("TF:")) taskForceCount  = value.substring(3).toInt();
  }
  else if (command == "PING")     { sendLora("PONG", getTeamName(localTeam)); }
  else if (command == "PONG")     { lastMessage = "LORA LINK CONFIRMED"; }
  else if (command == "BUZZ")     { buzz(200); }
  else if (command == "REVEAL" && value == "SCORES" && gameState == STATE_GAMEOVER) {
    adminScoreReveal = true;
    lastMessage = "SCORES REVEALED";
    beepShort();
  }
  else if (command == "TIMEUP") {
    gameTimeExpired = true;
    gameTimeExpiredMs = millis();
    lastMessage = "TIME UP";
  }
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

void drawBootSplash() {
  unsigned long startMs = millis();

  while (millis() - startMs < 3000) {
    int elapsed = millis() - startMs;
    int barWidth = map(elapsed, 0, 3000, 0, 112);
    if (barWidth < 0) barWidth = 0;
    if (barWidth > 112) barWidth = 112;

    display.clearBuffer();
    display.drawFrame(0, 0, 128, 64);
    drawCenteredText("AOJ", 31, u8g2_font_ncenB24_tr);
    drawCenteredText("Created by Nineteen", 43, u8g2_font_6x12_tf);
    display.drawFrame(8, 52, 112, 7);
    display.drawBox(8, 52, barWidth, 7);
    display.sendBuffer();
    delay(30);
  }
}

void drawCenteredText(const String &text, int y, const uint8_t *font) {
  display.setFont(font);
  int w = display.getStrWidth(text.c_str());
  int x = (128 - w) / 2;
  if (x < 0) x = 0;
  display.drawStr(x, y, text.c_str());
}

void drawHeader() {
  String title = getShortTeamName(localTeam) + " CP";
  int loraBars = (millis() - lastLoraSeenMs < 15000) ? 4 : 1;

  display.setFont(u8g2_font_6x12_tf);
  display.drawStr(3, 11, title.c_str());

  drawSignalBars(108, 11, loraBars);
  display.drawLine(0, 15, 128, 15);
}

void drawCtfRunningScreen() {
  display.drawFrame(0, 0, 128, 64);
  drawHeader();

  unsigned long elapsedMs = getElapsedGameMs();
  unsigned long durationMs = getGameDurationMs();
  unsigned long shownMs = (elapsedMs < durationMs) ? (durationMs - elapsedMs) : (elapsedMs - durationMs);
  int mm = (int)((shownMs / 1000UL) / 60UL);
  int ss = (int)((shownMs / 1000UL) % 60UL);
  String timeLine = elapsedMs < durationMs ? "LEFT " : "OT ";
  timeLine += String(mm) + ":" + (ss < 10 ? "0" : "") + String(ss);

  if (ctfHoldActive) {
    unsigned long heldMs = millis() - ctfHoldStartMs;
    if (heldMs > 3000) heldMs = 3000;

    int pct = map((int)heldMs, 0, 3000, 0, 100);
    drawCenteredText("CAPTURING", 30, u8g2_font_ncenB10_tr);
    String pctText = String(pct) + "%";
    drawCenteredText(pctText, 52, u8g2_font_ncenB14_tr);

    int progress = map((int)heldMs, 0, 3000, 0, 112);
    display.drawFrame(8, 58, 112, 5);
    display.drawBox(8, 58, progress, 5);
    return;
  }

  drawCenteredText("FLAG MODE", 33, u8g2_font_ncenB10_tr);
  drawCenteredText("HOLD RED TO CAPTURE", 50, u8g2_font_6x12_tf);
  drawCenteredText(timeLine, 62, u8g2_font_5x8_tf);
}

void drawGameOverScreen() {
  display.drawFrame(0, 0, 128, 64);
  drawHeader();

  if (gameMode == MODE_FLAG_CAPTURE && millis() < ctfCapturedBannerUntilMs) {
    drawCenteredText("CAPTURED", 40, u8g2_font_ncenB14_tr);
    if (gameOverReason.startsWith("FLAG CAPTURED BY ")) {
      String winner = gameOverReason.substring(17);
      drawCenteredText(winner, 60, u8g2_font_6x12_tf);
    }
    return;
  }

  drawCenteredText("GAME OVER", 40, u8g2_font_ncenB14_tr);

  if (gameMode == MODE_FLAG_CAPTURE && gameOverReason.startsWith("FLAG CAPTURED BY ")) {
    String winner = gameOverReason.substring(17);
    drawCenteredText(winner + " WIN", 56, u8g2_font_6x12_tf);
  }

  if (adminScoreReveal) {
    String counts = "BT:" + String(blackTalonCount) + " TF:" + String(taskForceCount);
    drawCenteredText(counts, 60, u8g2_font_6x12_tf);
  }
}

void drawDisplay() {
  display.clearBuffer();
  if (gameState == STATE_COUNTDOWN) {
    int remain = 0;
    if (countdownEndMs > millis()) {
      remain = (int)((countdownEndMs - millis() + 999UL) / 1000UL);
    }
    if (remain > GAME_START_COUNTDOWN_SECONDS) remain = GAME_START_COUNTDOWN_SECONDS;

    display.drawFrame(0, 0, 128, 64);
    drawHeader();
    drawCenteredText("GAME START", 27, u8g2_font_6x12_tf);
    drawCenteredText(String(remain), 62, u8g2_font_ncenB24_tr);
    display.sendBuffer();
    return;
  }

  if (gameState == STATE_RUNNING && millis() < gameStartBannerUntilMs) {
    display.drawFrame(0, 0, 128, 64);
    drawCenteredText("GAME START", 40, u8g2_font_ncenB14_tr);
    display.sendBuffer();
    return;
  }

  if (gameState == STATE_GAMEOVER) {
    drawGameOverScreen();
    display.sendBuffer();
    return;
  }

  display.drawFrame(0, 0, 128, 64);
  drawHeader();

  if (serverAdminDisabled) {
    drawCenteredText("DISARMED", 38, u8g2_font_ncenB10_tr);
    display.sendBuffer();
    return;
  }

  if (gameState == STATE_IDLE) {
    drawCenteredText(getGameModeName(gameMode), 33, u8g2_font_6x12_tf);
    drawCenteredText("PRESS READY", 54, u8g2_font_6x12_tf);
    display.sendBuffer();
    return;
  }

  if (gameState == STATE_READY) {
    drawCenteredText("READY CHECK", 32, u8g2_font_6x12_tf);
    String bt = blackTalonReady ? "BT READY" : "BT WAIT";
    String tf = taskForceReady  ? "TF READY" : "TF WAIT";
    drawCenteredText(bt + " " + tf, 54, u8g2_font_6x12_tf);
    display.sendBuffer();
    return;
  }

  if (gameMode == MODE_FLAG_CAPTURE) {
    drawCtfRunningScreen();
    display.sendBuffer();
    return;
  }

  if (gameMode == MODE_GAME_TIME) {
    drawCenteredText("GAME TIME", 28, u8g2_font_6x12_tf);

    unsigned long elapsedMs = getElapsedGameMs();
    unsigned long durationMs = getGameDurationMs();
    unsigned long shownMs = (elapsedMs < durationMs) ? (durationMs - elapsedMs) : (elapsedMs - durationMs);
    int mm = (int)((shownMs / 1000UL) / 60UL);
    int ss = (int)((shownMs / 1000UL) % 60UL);
    String timer = elapsedMs < durationMs ? "LEFT " : "OT ";
    timer += String(mm) + ":" + (ss < 10 ? "0" : "") + String(ss);
    drawCenteredText(timer, 50, u8g2_font_ncenB14_tr);
    display.sendBuffer();
    return;
  }

  String modeLine = getGameModeName(gameMode);
  if (modeLine.length() > 20) modeLine = modeLine.substring(0, 20);
  drawCenteredText(modeLine, 28, u8g2_font_6x12_tf);

  String scoreLine;
  if (hideOpponentScores && !adminScoreReveal) {
    if (localTeam == TEAM_BLACK_TALON) {
      scoreLine = "BT:" + String(blackTalonCount) + " TF:--";
    } else {
      scoreLine = "BT:-- TF:" + String(taskForceCount);
    }
  } else {
    scoreLine = "BT:" + String(blackTalonCount) + " TF:" + String(taskForceCount);
  }
  drawCenteredText(scoreLine, 44, u8g2_font_6x12_tf);

  unsigned long elapsedMs = getElapsedGameMs();
  unsigned long durationMs = getGameDurationMs();
  unsigned long shownMs = (elapsedMs < durationMs) ? (durationMs - elapsedMs) : (elapsedMs - durationMs);
  int mm = (int)((shownMs / 1000UL) / 60UL);
  int ss = (int)((shownMs / 1000UL) % 60UL);
  String timer = elapsedMs < durationMs ? "LEFT " : "OT ";
  timer += String(mm) + ":" + (ss < 10 ? "0" : "") + String(ss);
  if (modeUsesLimit(gameMode)) {
    timer += "  L:" + String(limitValue);
  }
  drawCenteredText(timer, 60, u8g2_font_5x8_tf);

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

  if (serverAdminDisabled || gameState == STATE_COUNTDOWN || gameState == STATE_RUNNING || gameState == STATE_GAMEOVER) {
    wasPressed = nowPressed;
    return;
  }

  if (nowPressed && !wasPressed) {
    markReady(localTeam, true);
  }

  wasPressed = nowPressed;
}

void handleActionButton() {
  static bool wasPressed = false;
  static unsigned long pressStartMs = 0;

  bool nowPressed = isButtonPressed(ACTION_BUTTON_PIN);

  if (serverAdminDisabled || gameState != STATE_RUNNING) {
    wasPressed = nowPressed;
    ctfHoldActive = false;
    ctfCaptureTriggered = false;
    ctfHoldStartMs = 0;
    return;
  }

  if (nowPressed && !wasPressed) {
    pressStartMs = millis();

    if (gameMode == MODE_FLAG_CAPTURE) {
      ctfHoldActive = true;
      ctfCaptureTriggered = false;
      ctfHoldStartMs = pressStartMs;
      buzz(80);
    }
  }

  if (nowPressed && gameMode == MODE_FLAG_CAPTURE) {
    ctfHoldActive = true;
    if (ctfHoldStartMs == 0) ctfHoldStartMs = pressStartMs;

    unsigned long heldMs = millis() - ctfHoldStartMs;
    if (!ctfCaptureTriggered && heldMs >= 3000) {
      ctfCaptureTriggered = true;
      ctfHoldActive = false;
      buzz(750);
      captureFlag();
    }
  }

  if (!nowPressed && wasPressed) {
    unsigned long heldMs = millis() - pressStartMs;

    if (gameMode == MODE_FLAG_CAPTURE) {
      ctfHoldActive = false;
      ctfHoldStartMs = 0;
      ctfCaptureTriggered = false;
    } else if (heldMs < 3000) {
      registerActionPress();
    }
  }

  wasPressed = nowPressed;
}

void handleAdminRevealButtons() {
  static unsigned long bothHoldStartMs = 0;
  static unsigned long readyHoldStartMs = 0;

  if (gameState != STATE_GAMEOVER || serverAdminDisabled) {
    bothHoldStartMs = 0;
    readyHoldStartMs = 0;
    return;
  }

  bool readyPressed = isButtonPressed(READY_BUTTON_PIN);
  bool actionPressed = isButtonPressed(ACTION_BUTTON_PIN);

  if (readyPressed && actionPressed) {
    readyHoldStartMs = 0;

    if (bothHoldStartMs == 0) {
      bothHoldStartMs = millis();
      return;
    }

    if (millis() - bothHoldStartMs >= 3000) {
      adminScoreReveal = true;
      lastMessage = "ADMIN REVEAL SCORES";
      sendLora("REVEAL", "SCORES");
      beepShort();
      bothHoldStartMs = 0;
    }
    return;
  }

  readyHoldStartMs = 0;

  if (readyPressed && !actionPressed) {
    if (readyHoldStartMs == 0) {
      readyHoldStartMs = millis();
      return;
    }

    if (millis() - readyHoldStartMs >= 3000) {
      lastMessage = "ADMIN RESET GAME";
      resetGame(true);
      readyHoldStartMs = 0;
    }
    return;
  }

  readyHoldStartMs = 0;
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
  page += "<div class='stat'><div class='label'>BT Status</div><div class='value'>" + getReadyStatusLabel(blackTalonReady) + "</div></div>";
  page += "<div class='stat'><div class='label'>TF Status</div><div class='value'>" + getReadyStatusLabel(taskForceReady) + "</div></div>";
  page += "<div class='stat'><div class='label'>Mode</div><div class='value'>" + getGameModeName(gameMode) + "</div></div>";
  page += "<div class='stat'><div class='label'>Timer</div><div class='value'>" + String(getGameTimerMinutesSafe()) + " min</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Game Results</h2><div class='row'>";
  if (canShowAllScores()) {
    page += "<div class='stat'><div class='label red'>Black Talon</div><div class='value'>" + String(blackTalonCount) + "</div></div>";
    page += "<div class='stat'><div class='label blue'>Task Force</div><div class='value'>" + String(taskForceCount) + "</div></div>";
  } else {
    page += "<div class='stat'><div class='label red'>Black Talon</div><div class='value'>";
    page += localTeam == TEAM_BLACK_TALON ? String(blackTalonCount) : String("--");
    page += "</div></div>";
    page += "<div class='stat'><div class='label blue'>Task Force</div><div class='value'>";
    page += localTeam == TEAM_TASK_FORCE ? String(taskForceCount) : String("--");
    page += "</div></div>";
  }
  page += "<div class='stat'><div class='label'>Limit</div><div class='value'>" + String(limitValue) + "</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Score Visibility</h2>";
  page += "<form action='/togglescores' method='GET'>";
  page += "<label class='mode-option'><input type='radio' name='hidden' value='1'" + checkedHideOpponentIf(true) + "> Hide Opponent Score</label>";
  page += "<label class='mode-option'><input type='radio' name='hidden' value='0'" + checkedHideOpponentIf(false) + "> Show Both Scores</label>";
  page += "<button type='submit'>SAVE VISIBILITY</button>";
  page += "</form>";
  page += "<p class='small'>Use READY + ACTION hold after game over to reveal hidden scores.</p>";
  page += "</div>";

  page += "<div class='panel'><h2>Game Mode</h2>";
  page += "<form action='/setmode' method='GET'>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='deathmatch'" + checkedIf(MODE_DEATHMATCH_COUNTER) + "> Deathmatch Counter</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='killlimit'" + checkedIf(MODE_KILL_LIMIT) + "> Kill Limit</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='respawnlimit'" + checkedIf(MODE_RESPAWN_LIMIT) + "> Limited Respawns</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='flag'" + checkedIf(MODE_FLAG_CAPTURE) + "> Flag Capture</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='gametime'" + checkedIf(MODE_GAME_TIME) + "> Game Time</label>";
  page += "<button type='submit'>ACTIVATE MODE</button>";
  page += "</form>";
  page += "<p class='small'>Mode applies locally first, then can be pushed to the second CP unit by LoRa.</p>";
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
  page += "<p>Countdown Seconds<br><input type='number' name='countdown' value='" + String(GAME_START_COUNTDOWN_SECONDS) + "'></p>";
  page += "<p>Game Timer Minutes<br><input type='number' name='gametimer' value='" + String(getGameTimerMinutesSafe()) + "'></p>";
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
    if (server.hasArg("countdown")) countdownSeconds    = GAME_START_COUNTDOWN_SECONDS;
    if (server.hasArg("gametimer")) gameTimerMinutes    = server.arg("gametimer").toInt();
    if (server.hasArg("respawn"))   respawnDelaySeconds = server.arg("respawn").toInt();

    if (limitValue < 1)          limitValue = 1;
    countdownSeconds = GAME_START_COUNTDOWN_SECONDS;
    if (gameTimerMinutes < 1)    gameTimerMinutes = 1;
    if (gameTimerMinutes > 180)  gameTimerMinutes = 180;
    if (respawnDelaySeconds < 0) respawnDelaySeconds = 0;

    saveSettings();

    pendingLoraSync   = true;
    queueSettingsSync();

    redirectHome();
  });

  server.on("/togglescores", HTTP_GET, []() {
    if (!server.hasArg("hidden")) {
      server.send(400, "text/plain", "NO VISIBILITY SELECTED");
      return;
    }

    hideOpponentScores = server.arg("hidden") != "0";
    adminScoreReveal = false;
    saveSettings();

    pendingLoraSync   = true;
    queueSettingsSync();
    redirectHome();
  });

  server.on("/pushsettings", HTTP_GET, []() {
    queueSettingsSync();
    redirectHome();
  });

  server.on("/ready",    HTTP_GET, []() { markReady(localTeam, true); redirectHome(); });
  server.on("/start",    HTTP_GET, []() { beginGameCountdown(true);   redirectHome(); });
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
  drawBootSplash();

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
  updateBuzzer();
  server.handleClient();

  receiveLora();

  handleReadyButton();
  handleActionButton();
  handleAdminRevealButtons();

  // Countdown → synchronized ticks, beeps, then game start
  if (gameState == STATE_COUNTDOWN) {
    int remain = 0;
    if (countdownEndMs > millis()) {
      remain = (int)((countdownEndMs - millis() + 999UL) / 1000UL);
    }
    if (remain > GAME_START_COUNTDOWN_SECONDS) remain = GAME_START_COUNTDOWN_SECONDS;

    if (remain > 0 && remain <= GAME_START_COUNTDOWN_SECONDS && remain != lastCountdownBeepSecond) {
      lastCountdownBeepSecond = remain;
      buzz(remain == 1 ? 250 : 100);
    }

    if (countdownEndMs > 0 && millis() >= countdownEndMs) {
      startGame(countdownMaster);
    }
  }

  if (gameState == STATE_RUNNING && gameStartMs > 0) {
    unsigned long elapsedMs = getElapsedGameMs();
    unsigned long durationMs = getGameDurationMs();

    if (!gameTimeExpired && elapsedMs >= durationMs) {
      gameTimeExpired = true;
      gameTimeExpiredMs = millis();
      sendLora("TIMEUP", String(getGameTimerMinutesSafe()));

      if (gameMode == MODE_FLAG_CAPTURE) {
        setGameOver("TIME UP", true);
      } else {
        lastMessage = "TIME UP - OVERTIME";
      }
    }

    if (gameTimeExpired && gameMode == MODE_DEATHMATCH_COUNTER
        && millis() - gameTimeExpiredMs >= DEATHMATCH_GRACE_MS) {
      setGameOver("TIME UP +2 MIN", true);
    }
  }

  // Pending peer SYNC broadcast
  if (pendingLoraSync) {
    pendingLoraSync = false;
    sendLora("SYNC", pendingSyncMessage);
  }

  // Peer status broadcast every 5 s
  if (millis() - lastStatusSendMs > 5000) {
    lastStatusSendMs = millis();
    sendLora("STATUS", getServerStateString());
  }

  // Server heartbeat every 15 s
  if (millis() - lastServerHeartbeatMs > 15000) {
    lastServerHeartbeatMs = millis();
    sendStatus();

#if defined(USE_WIFI) && USE_WIFI == 1
    aojWifi.reportStatus(DEVICE_ID, getServerStateString().c_str(),
             0, lora.rssiPercent(), FW_VERSION);
#endif
  }

  if (millis() - lastDisplayUpdateMs > 100) {
    lastDisplayUpdateMs = millis();
    drawDisplay();
  }

  forceLedsOff();
  delay(5);
}
