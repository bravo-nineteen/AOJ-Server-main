/**
 * respawn_station_dual_team.ino
 *
 * Heltec WiFi LoRa 32 V3 dual-team respawn/checkpoint unit.
 *
 * This sketch keeps the local peer-to-peer coordination flow from the custom
 * checkpoint design while also speaking the AOJ server LoRa protocol:
 *
 *   Server protocol: AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 *   Peer protocol:   AOJCP|senderTeam|COMMAND|VALUE
 *
 * The backend ignores AOJCP frames, while STATUS / RESPAWN / ACK / GAMEOVER
 * frames are visible to AOJ Command OS.
 */

#define BOARD_HELTEC_V3

#define DEVICE_ID        "RESPAWN-RED-01"
#define PEER_DEVICE_ID   "RESPAWN-BLUE-01"
#define PROP_TYPE        "RespawnStationDual"
#define FW_VERSION       "1.0.0"

#define USE_WIFI         0
#define WIFI_SSID        "AOJ_Server"
#define WIFI_PASS        "AOJ2023"
#define SERVER_URL       "http://192.168.1.100:8000"
#define PROP_TOKEN       ""

#define LORA_FREQUENCY   923.0
#define BATTERY_ADC_PIN  1

#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Preferences.h>
#include <AOJ_Core.h>

#define READY_BUTTON_PIN   33
#define ACTION_BUTTON_PIN  34
#define BUZZER_PIN         47
#define LED_PIN_1          35
#define LED_PIN_2          36

#define PORTAL_PASSWORD            "aojcheckpoint"
#define HEARTBEAT_INTERVAL_MS      30000UL
#define DISPLAY_REFRESH_MS         250UL
#define SERVER_STATUS_REFRESH_MS   5000UL
#define PEER_PACKET_HEADER         "AOJCP|"

AojLoRa lora;
AojWiFi aojWifi;
WebServer server(80);
Preferences prefs;
U8G2_SSD1309_128X64_NONAME0_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

enum Team {
  TEAM_RED = 0,
  TEAM_BLUE = 1
};

enum GameMode {
  MODE_RECORD_ONLY = 0,
  MODE_KILL_LIMIT = 1,
  MODE_RESPAWN_LIMIT = 2,
  MODE_FLAG_CAPTURE = 3
};

enum GameState {
  STATE_IDLE = 0,
  STATE_READY = 1,
  STATE_COUNTDOWN = 2,
  STATE_RUNNING = 3,
  STATE_GAMEOVER = 4
};

Team localTeam = TEAM_RED;
GameMode gameMode = MODE_RECORD_ONLY;
GameState gameState = STATE_IDLE;

bool adminEnabled = true;
bool redReady = false;
bool blueReady = false;

int redCount = 0;
int blueCount = 0;

int limitValue = 20;
int countdownSeconds = 10;
int respawnDelaySeconds = 5;

bool pendingPeerSync = false;
String pendingSyncMessage;

bool portalEnabled = false;
String portalSsid;

unsigned long countdownStartMs = 0;
unsigned long lastHeartbeatMs = 0;
unsigned long lastDisplayUpdateMs = 0;
unsigned long lastServerStatusMs = 0;
unsigned long lastPeerSeenMs = 0;

String lastMessage = "BOOT";
String gameOverReason;

int lastRssiPercent = 0;

String teamName(Team team) {
  return team == TEAM_RED ? "RED" : "BLUE";
}

String shortTeamName(Team team) {
  return team == TEAM_RED ? "RED" : "BLUE";
}

String gameModeName(GameMode mode) {
  switch (mode) {
    case MODE_RECORD_ONLY: return "RECORD ONLY";
    case MODE_KILL_LIMIT: return "KILL LIMIT";
    case MODE_RESPAWN_LIMIT: return "RESPAWN LIMIT";
    case MODE_FLAG_CAPTURE: return "FLAG CAPTURE";
  }
  return "UNKNOWN";
}

String gameModeValue(GameMode mode) {
  switch (mode) {
    case MODE_RECORD_ONLY: return "record";
    case MODE_KILL_LIMIT: return "killlimit";
    case MODE_RESPAWN_LIMIT: return "respawnlimit";
    case MODE_FLAG_CAPTURE: return "flag";
  }
  return "record";
}

String gameStateName(GameState state) {
  switch (state) {
    case STATE_IDLE: return "IDLE";
    case STATE_READY: return "READY";
    case STATE_COUNTDOWN: return "COUNTDOWN";
    case STATE_RUNNING: return "RUNNING";
    case STATE_GAMEOVER: return "GAME OVER";
  }
  return "UNKNOWN";
}

String serverStateLabel() {
  if (!adminEnabled) return "disarmed";
  if (gameState == STATE_GAMEOVER) return "alarm";
  return "online";
}

String checkedIf(GameMode mode) {
  return gameMode == mode ? " checked" : "";
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

int batteryPercent() {
  return aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
}

int localCount() {
  return localTeam == TEAM_RED ? redCount : blueCount;
}

int peerCount() {
  return localTeam == TEAM_RED ? blueCount : redCount;
}

int remainingRespawnsForLocalTeam() {
  if (gameMode != MODE_RESPAWN_LIMIT) return -1;
  int remaining = limitValue - localCount();
  return remaining < 0 ? 0 : remaining;
}

void saveSettings() {
  prefs.begin("aojrspn", false);
  prefs.putUInt("team", (uint32_t)localTeam);
  prefs.putUInt("mode", (uint32_t)gameMode);
  prefs.putInt("limit", limitValue);
  prefs.putInt("countdown", countdownSeconds);
  prefs.putInt("respawn", respawnDelaySeconds);
  prefs.putBool("enabled", adminEnabled);
  prefs.end();
}

void loadSettings() {
  prefs.begin("aojrspn", false);
  localTeam = (Team)prefs.getUInt("team", (uint32_t)TEAM_RED);
  gameMode = (GameMode)prefs.getUInt("mode", (uint32_t)MODE_RECORD_ONLY);
  limitValue = prefs.getInt("limit", 20);
  countdownSeconds = prefs.getInt("countdown", 10);
  respawnDelaySeconds = prefs.getInt("respawn", 5);
  adminEnabled = prefs.getBool("enabled", true);
  prefs.end();

  if (limitValue < 1) limitValue = 1;
  if (countdownSeconds < 1) countdownSeconds = 1;
  if (respawnDelaySeconds < 0) respawnDelaySeconds = 0;
}

void sendServerFrame(const String &command, const String &value, const String &messageId) {
  String frame = aojBuildFrame(DEVICE_ID, command, value, messageId);
  lora.send(frame);
  forceLedsOff();
}

void sendAck(const String &messageId, const String &value = "OK") {
  sendServerFrame("ACK", value, messageId);
}

void sendPeerPacket(const String &command, const String &value) {
  String packet = String(PEER_PACKET_HEADER) + String((int)localTeam) + "|" + command + "|" + value;
  lora.send(packet);
  forceLedsOff();
}

void sendStatus() {
  int battery = batteryPercent();
  int rssi = lora.rssiPercent();
  lastRssiPercent = rssi;

  String value = serverStateLabel() + ":" +
                 teamName(localTeam) + ":" +
                 gameStateName(gameState) + ":" +
                 gameModeValue(gameMode) + ":" +
                 String(localCount()) + ":" +
                 String(peerCount()) + ":" +
                 String(limitValue) + ":" +
                 String(respawnDelaySeconds) + ":" +
                 PROP_TYPE;

  sendServerFrame("STATUS", value, aojGenerateMessageId());
  aojWifi.reportStatus(DEVICE_ID, serverStateLabel().c_str(), battery, rssi, FW_VERSION);
}

void sendRespawnEvent() {
  String value = teamName(localTeam) + ":" + String(remainingRespawnsForLocalTeam());
  sendServerFrame("RESPAWN", value, aojGenerateMessageId());
}

void sendGameOverEvent(const String &reason) {
  sendServerFrame("GAMEOVER", reason, aojGenerateMessageId());
}

void queuePeerSync() {
  pendingPeerSync = true;
  pendingSyncMessage = "MODE:" + gameModeValue(gameMode) +
                       ";LIMIT:" + String(limitValue) +
                       ";COUNTDOWN:" + String(countdownSeconds) +
                       ";RESPAWN:" + String(respawnDelaySeconds);
}

void applyModeString(const String &selectedMode, bool broadcastPeer) {
  if (selectedMode == "record") {
    gameMode = MODE_RECORD_ONLY;
  } else if (selectedMode == "killlimit") {
    gameMode = MODE_KILL_LIMIT;
  } else if (selectedMode == "respawnlimit") {
    gameMode = MODE_RESPAWN_LIMIT;
  } else if (selectedMode == "flag") {
    gameMode = MODE_FLAG_CAPTURE;
  } else {
    gameMode = MODE_RECORD_ONLY;
  }

  saveSettings();
  lastMessage = "MODE " + gameModeName(gameMode);

  if (broadcastPeer) {
    queuePeerSync();
  }
}

void applySyncMessage(const String &message) {
  int start = 0;

  while (start < message.length()) {
    int end = message.indexOf(';', start);
    if (end == -1) end = message.length();

    String part = message.substring(start, end);
    int sep = part.indexOf(':');

    if (sep > 0) {
      String key = part.substring(0, sep);
      String value = part.substring(sep + 1);

      if (key == "MODE") applyModeString(value, false);
      if (key == "LIMIT") limitValue = max(1, value.toInt());
      if (key == "COUNTDOWN") countdownSeconds = max(1, value.toInt());
      if (key == "RESPAWN") respawnDelaySeconds = max(0, value.toInt());
    }

    start = end + 1;
  }

  saveSettings();
  lastMessage = "SYNCED";
  beepShort();
}

void resetGame(bool broadcastPeer) {
  redReady = false;
  blueReady = false;
  redCount = 0;
  blueCount = 0;
  gameOverReason = "";
  gameState = STATE_IDLE;
  lastMessage = adminEnabled ? "RESET" : "DISABLED";

  if (broadcastPeer) {
    sendPeerPacket("RESET", "GAME");
  }

  sendStatus();
}

void setGameOver(const String &reason, bool broadcastPeer, bool reportServer) {
  gameState = STATE_GAMEOVER;
  gameOverReason = reason;
  lastMessage = "GAMEOVER " + reason;

  buzzPatternGameOver();

  if (broadcastPeer) {
    sendPeerPacket("GAMEOVER", reason);
  }
  if (reportServer) {
    sendGameOverEvent(reason);
  }

  sendStatus();
}

void startGame(bool broadcastPeer) {
  if (!adminEnabled) return;

  gameState = STATE_RUNNING;
  lastMessage = "GAME START";
  buzz(300);

  if (broadcastPeer) {
    sendPeerPacket("START", "GAME");
  }

  sendStatus();
}

void markReady(Team team, bool broadcastPeer) {
  if (!adminEnabled || gameState == STATE_GAMEOVER) return;

  if (team == TEAM_RED) redReady = true;
  if (team == TEAM_BLUE) blueReady = true;

  gameState = STATE_READY;
  lastMessage = teamName(team) + " READY";
  beepShort();

  if (broadcastPeer) {
    sendPeerPacket("READY", String((int)team));
  }

  if (redReady && blueReady) {
    gameState = STATE_COUNTDOWN;
    countdownStartMs = millis();
    sendPeerPacket("COUNTDOWN", String(countdownSeconds));
  }

  sendStatus();
}

void registerActionPress() {
  if (!adminEnabled || gameState != STATE_RUNNING) return;

  if (localTeam == TEAM_RED) {
    redCount++;
    sendPeerPacket("COUNT", "RED:" + String(redCount));
  } else {
    blueCount++;
    sendPeerPacket("COUNT", "BLUE:" + String(blueCount));
  }

  sendRespawnEvent();
  beepShort();

  if (gameMode == MODE_KILL_LIMIT) {
    if (redCount >= limitValue) setGameOver("RED HIT KILL LIMIT", true, true);
    if (blueCount >= limitValue) setGameOver("BLUE HIT KILL LIMIT", true, true);
  }

  if (gameMode == MODE_RESPAWN_LIMIT) {
    if (redCount >= limitValue) setGameOver("RED RESPAWNS EXHAUSTED", true, true);
    if (blueCount >= limitValue) setGameOver("BLUE RESPAWNS EXHAUSTED", true, true);
  }

  sendStatus();
}

void captureFlag() {
  if (!adminEnabled || gameState != STATE_RUNNING) return;
  setGameOver("FLAG CAPTURED BY " + teamName(localTeam), true, true);
}

void handlePeerPacket(const String &packet) {
  if (!packet.startsWith(PEER_PACKET_HEADER)) return;

  int p1 = packet.indexOf('|');
  int p2 = packet.indexOf('|', p1 + 1);
  int p3 = packet.indexOf('|', p2 + 1);
  if (p1 < 0 || p2 < 0 || p3 < 0) return;

  int senderTeam = packet.substring(p1 + 1, p2).toInt();
  String command = packet.substring(p2 + 1, p3);
  String value = packet.substring(p3 + 1);

  if (senderTeam == (int)localTeam) return;

  lastPeerSeenMs = millis();
  lastMessage = command + " " + value;

  if (command == "READY") {
    markReady((Team)value.toInt(), false);
  } else if (command == "COUNTDOWN") {
    countdownSeconds = max(1, value.toInt());
    gameState = STATE_COUNTDOWN;
    countdownStartMs = millis();
  } else if (command == "START") {
    startGame(false);
  } else if (command == "RESET") {
    resetGame(false);
  } else if (command == "GAMEOVER") {
    setGameOver(value, false, false);
  } else if (command == "COUNT") {
    if (value.startsWith("RED:")) redCount = value.substring(4).toInt();
    if (value.startsWith("BLUE:")) blueCount = value.substring(5).toInt();
  } else if (command == "PING") {
    sendPeerPacket("PONG", teamName(localTeam));
  } else if (command == "PONG") {
    lastMessage = "PEER LINK OK";
  } else if (command == "SYNC") {
    applySyncMessage(value);
  } else if (command == "HELLO") {
    lastMessage = "PEER ONLINE";
  }
}

void handleServerCommand(const AOJFrame &frame) {
  if (frame.command == "STATUS_REQUEST") {
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "RESET") {
    adminEnabled = true;
    saveSettings();
    resetGame(true);
    sendAck(frame.messageId);
  }
  else if (frame.command == "ENABLE" || frame.command == "ARM") {
    adminEnabled = true;
    if (gameState == STATE_GAMEOVER) gameState = STATE_IDLE;
    saveSettings();
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "DISABLE" || frame.command == "DISARM") {
    adminEnabled = false;
    gameState = STATE_IDLE;
    redReady = false;
    blueReady = false;
    saveSettings();
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "TRIGGER_ALARM" || frame.command == "GAMEOVER") {
    sendAck(frame.messageId);
    setGameOver("ADMIN ENDED GAME", true, true);
  }
  else if (frame.command == "START") {
    sendAck(frame.messageId);
    startGame(true);
  }
  else if (frame.command == "SET_MODE") {
    applyModeString(frame.value, true);
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "SET_LIMIT" || frame.command == "SET_RESPAWN_COUNT") {
    int parsed = frame.value.toInt();
    if (parsed >= 1) {
      limitValue = parsed;
      saveSettings();
      queuePeerSync();
    }
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "SET_COUNTDOWN") {
    int parsed = frame.value.toInt();
    if (parsed >= 1) {
      countdownSeconds = parsed;
      saveSettings();
      queuePeerSync();
    }
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "SET_RESPAWN_DELAY") {
    int parsed = frame.value.toInt();
    if (parsed >= 0) {
      respawnDelaySeconds = parsed;
      saveSettings();
      queuePeerSync();
    }
    sendAck(frame.messageId);
    sendStatus();
  }
  else if (frame.command == "SET_TEAM") {
    if (frame.value == "RED") localTeam = TEAM_RED;
    if (frame.value == "BLUE") localTeam = TEAM_BLUE;
    saveSettings();
    sendAck(frame.messageId);
    sendStatus();
  }
  else {
    sendAck(frame.messageId, "UNKNOWN");
  }
}

void receiveLoRa() {
  if (!lora.available()) return;

  String raw = lora.read();
  if (raw.length() == 0) return;

  if (raw.startsWith("AOJ|")) {
    AOJFrame frame = aojParseFrame(raw);
    if (!frame.valid) return;
    if (frame.deviceId != DEVICE_ID && frame.deviceId != "*") return;
    handleServerCommand(frame);
    return;
  }

  if (raw.startsWith(PEER_PACKET_HEADER)) {
    handlePeerPacket(raw);
  }
}

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
  display.drawStr(3, 10, "AOJ RESPAWN");

  int wifiBars = portalEnabled ? 4 : 1;
  int peerBars = (millis() - lastPeerSeenMs < 15000UL) ? 4 : 1;

  display.drawStr(84, 10, "W");
  drawSignalBars(92, 10, wifiBars);
  display.drawStr(105, 10, "P");
  drawSignalBars(113, 10, peerBars);
  display.drawLine(0, 14, 128, 14);

  display.drawStr(4, 26, shortTeamName(localTeam).c_str());
  display.drawStr(34, 26, gameStateName(gameState).c_str());

  String modeLine = gameModeName(gameMode);
  if (modeLine.length() > 20) modeLine = modeLine.substring(0, 20);
  display.drawStr(4, 38, modeLine.c_str());

  String counts = "R:" + String(redCount) + " B:" + String(blueCount) + " L:" + String(limitValue);
  display.drawStr(4, 50, counts.c_str());

  if (!adminEnabled) {
    display.drawStr(4, 62, "DISABLED BY SERVER");
  } else if (gameState == STATE_GAMEOVER) {
    display.drawStr(4, 62, "ADMIN RESET REQUIRED");
  } else if (gameState == STATE_COUNTDOWN) {
    int remain = countdownSeconds - ((millis() - countdownStartMs) / 1000UL);
    if (remain < 0) remain = 0;
    String cd = "START IN " + String(remain);
    display.drawStr(4, 62, cd.c_str());
  } else {
    String status = "BAT " + String(batteryPercent()) + "% RSSI " + String(lastRssiPercent) + "%";
    display.drawStr(4, 62, status.c_str());
  }

  display.sendBuffer();
}

bool isButtonPressed(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

void handleReadyButton() {
  static bool wasPressed = false;

  bool nowPressed = isButtonPressed(READY_BUTTON_PIN);
  if (nowPressed && !wasPressed) {
    markReady(localTeam, true);
  }

  wasPressed = nowPressed;
}

void handleActionButton() {
  static bool wasPressed = false;
  static unsigned long pressStartMs = 0;
  static bool flagCaptured = false;

  bool nowPressed = isButtonPressed(ACTION_BUTTON_PIN);

  if (nowPressed && !wasPressed) {
    pressStartMs = millis();
    flagCaptured = false;
  }

  if (nowPressed && !flagCaptured && gameMode == MODE_FLAG_CAPTURE && millis() - pressStartMs >= 3000UL) {
    flagCaptured = true;
    captureFlag();
  }

  if (!nowPressed && wasPressed) {
    unsigned long heldMs = millis() - pressStartMs;
    if (heldMs < 3000UL && gameMode != MODE_FLAG_CAPTURE) {
      registerActionPress();
    }
  }

  wasPressed = nowPressed;
}

String css() {
  return R"rawliteral(
<style>
body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#050505;color:#ddd;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:22px 22px;}
.wrap{max-width:760px;margin:auto;padding:18px;}
.brand{color:#d71920;font-size:24px;font-weight:900;letter-spacing:1px;white-space:nowrap;text-transform:uppercase;}
.title{font-size:36px;font-weight:900;color:white;margin:6px 0 18px 0;letter-spacing:2px;}
.panel{background:#0b0b0b;border:1px solid #2a2a2a;margin:14px 0;padding:14px;box-shadow:0 0 14px rgba(215,25,32,.16);}
h2{font-size:16px;color:#fff;margin:0 0 12px 0;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:8px;}
.row{display:flex;gap:10px;flex-wrap:wrap;}
.stat{background:#121212;border:1px solid #333;padding:10px;flex:1;min-width:135px;}
.label{color:#999;font-size:11px;text-transform:uppercase;}
.value{color:#fff;font-size:18px;font-weight:800;margin-top:4px;}
.red{color:#d71920;}.blue{color:#4aa3ff;}
button{background:#d71920;color:white;border:0;padding:13px 16px;margin:5px 4px 5px 0;font-weight:900;border-radius:3px;letter-spacing:.5px;}
button.secondary{background:#222;border:1px solid #555;}button.warn{background:#ff9d00;color:#111;}button.dark{background:#111;border:1px solid #666;}
input[type=number]{background:#111;color:white;border:1px solid #555;padding:12px;width:110px;font-size:16px;}
.mode-option{display:block;background:#121212;border:1px solid #333;margin:8px 0;padding:12px;font-weight:800;}
.mode-option input{transform:scale(1.35);margin-right:10px;}
a{color:white;text-decoration:none;}.small{font-size:12px;color:#aaa;}.gameover{border:2px solid #d71920;background:#180506;}
</style>
)rawliteral";
}

String htmlPage() {
  String page = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
  page += css();
  page += "</head><body><div class='wrap'>";
  page += "<div class='brand'>Airsoft Online Japan</div>";
  page += "<div class='title'>DUAL TEAM RESPAWN</div>";

  if (gameState == STATE_GAMEOVER) {
    page += "<div class='panel gameover'><h2>GAME OVER</h2><div class='value red'>" + gameOverReason + "</div><p class='small'>Admin reset required before next game.</p></div>";
  }

  page += "<div class='panel'><h2>Status</h2><div class='row'>";
  page += "<div class='stat'><div class='label'>Device</div><div class='value'>" + String(DEVICE_ID) + "</div></div>";
  page += "<div class='stat'><div class='label'>Team</div><div class='value'>" + teamName(localTeam) + "</div></div>";
  page += "<div class='stat'><div class='label'>State</div><div class='value'>" + gameStateName(gameState) + "</div></div>";
  page += "<div class='stat'><div class='label'>Mode</div><div class='value'>" + gameModeName(gameMode) + "</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Counts</h2><div class='row'>";
  page += "<div class='stat'><div class='label red'>Red</div><div class='value'>" + String(redCount) + "</div></div>";
  page += "<div class='stat'><div class='label blue'>Blue</div><div class='value'>" + String(blueCount) + "</div></div>";
  page += "<div class='stat'><div class='label'>Limit</div><div class='value'>" + String(limitValue) + "</div></div>";
  page += "<div class='stat'><div class='label'>Battery</div><div class='value'>" + String(batteryPercent()) + "%</div></div>";
  page += "</div></div>";

  page += "<div class='panel'><h2>Game Mode</h2><form action='/setmode' method='GET'>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='record'" + checkedIf(MODE_RECORD_ONLY) + "> Record Only</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='killlimit'" + checkedIf(MODE_KILL_LIMIT) + "> Kill Limit</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='respawnlimit'" + checkedIf(MODE_RESPAWN_LIMIT) + "> Limited Respawns</label>";
  page += "<label class='mode-option'><input type='radio' name='mode' value='flag'" + checkedIf(MODE_FLAG_CAPTURE) + "> Flag Capture</label>";
  page += "<button type='submit'>ACTIVATE MODE</button></form>";
  page += "<p class='small'>This updates the local unit first, then syncs the partner unit using peer LoRa packets.</p></div>";

  page += "<div class='panel'><h2>Settings</h2><form action='/settings' method='GET'>";
  page += "<p>Kill / Respawn Limit<br><input type='number' name='limit' value='" + String(limitValue) + "'></p>";
  page += "<p>Countdown Seconds<br><input type='number' name='countdown' value='" + String(countdownSeconds) + "'></p>";
  page += "<p>Respawn Delay Seconds<br><input type='number' name='respawn' value='" + String(respawnDelaySeconds) + "'></p>";
  page += "<button type='submit'>SAVE AND SYNC</button></form></div>";

  page += "<div class='panel'><h2>Admin Controls</h2>";
  page += "<a href='/ready'><button class='secondary'>FORCE READY</button></a>";
  page += "<a href='/start'><button>FORCE START</button></a>";
  page += "<a href='/gameover'><button class='warn'>END GAME</button></a>";
  page += "<a href='/reset'><button class='dark'>RESET</button></a>";
  page += "<a href='/ping'><button class='secondary'>TEST PEER LINK</button></a>";
  page += "<a href='/beep'><button class='secondary'>BUZZER TEST</button></a>";
  page += "</div>";

  page += "<div class='panel'><h2>Diagnostics</h2><div class='small'>Peer: " + String(PEER_DEVICE_ID) + "<br>Last message: " + lastMessage + "<br>Portal SSID: " + portalSsid + "<br>Server status: " + serverStateLabel() + "</div></div>";
  page += "<script>setTimeout(()=>{location.reload();},5000);</script>";
  page += "</div></body></html>";
  return page;
}

void redirectHome() {
  server.sendHeader("Location", "/");
  server.send(303, "text/plain", "");
}

String buildPortalSsid() {
  uint32_t suffix = (uint32_t)(ESP.getEfuseMac() & 0xFFFFULL);
  char buf[5];
  snprintf(buf, sizeof(buf), "%04X", (unsigned int)suffix);
  return String("AOJ-CHECKPOINT-") + String(buf);
}

void setupPortal() {
  portalEnabled = true;
  portalSsid = buildPortalSsid();

  WiFi.mode(WIFI_AP);
  WiFi.setSleep(false);
  WiFi.softAP(portalSsid.c_str(), PORTAL_PASSWORD, 6, 0, 4);

  server.on("/", HTTP_GET, []() {
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

  server.on("/settings", HTTP_GET, []() {
    if (server.hasArg("limit")) limitValue = max(1, server.arg("limit").toInt());
    if (server.hasArg("countdown")) countdownSeconds = max(1, server.arg("countdown").toInt());
    if (server.hasArg("respawn")) respawnDelaySeconds = max(0, server.arg("respawn").toInt());
    saveSettings();
    queuePeerSync();
    redirectHome();
  });

  server.on("/ready", HTTP_GET, []() {
    markReady(localTeam, true);
    redirectHome();
  });

  server.on("/start", HTTP_GET, []() {
    startGame(true);
    redirectHome();
  });

  server.on("/reset", HTTP_GET, []() {
    resetGame(true);
    redirectHome();
  });

  server.on("/gameover", HTTP_GET, []() {
    setGameOver("ADMIN ENDED GAME", true, true);
    redirectHome();
  });

  server.on("/ping", HTTP_GET, []() {
    sendPeerPacket("PING", "TEST");
    redirectHome();
  });

  server.on("/beep", HTTP_GET, []() {
    buzz(120);
    redirectHome();
  });

  server.begin();
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(READY_BUTTON_PIN, INPUT_PULLUP);
  pinMode(ACTION_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN_1, OUTPUT);
  pinMode(LED_PIN_2, OUTPUT);
  forceLedsOff();

  analogReadResolution(12);

  loadSettings();

  Wire.begin(17, 18);
  display.begin();
  display.clearBuffer();
  display.setFont(u8g2_font_6x12_tf);
  display.drawStr(0, 12, "AOJ RESPAWN");
  display.drawStr(0, 28, "BOOTING...");
  display.sendBuffer();

  if (!lora.begin()) {
    display.clearBuffer();
    display.drawStr(0, 12, "LORA INIT FAIL");
    display.sendBuffer();
    while (true) { delay(1000); }
  }

  aojWifi.begin(WIFI_SSID, WIFI_PASS, SERVER_URL, PROP_TOKEN);

  if (isButtonPressed(READY_BUTTON_PIN)) {
    setupPortal();
  }

  lastMessage = "LORA READY";
  sendPeerPacket("HELLO", teamName(localTeam));
  sendStatus();
  lastHeartbeatMs = millis();
  lastServerStatusMs = millis();
  buzz(120);
}

void loop() {
  if (portalEnabled) {
    server.handleClient();
  }

  receiveLoRa();

  if (adminEnabled) {
    handleReadyButton();
    handleActionButton();
  }

  if (gameState == STATE_COUNTDOWN) {
    unsigned long elapsedSeconds = (millis() - countdownStartMs) / 1000UL;
    if (elapsedSeconds >= (unsigned long)countdownSeconds) {
      startGame(true);
    }
  }

  if (pendingPeerSync) {
    pendingPeerSync = false;
    sendPeerPacket("SYNC", pendingSyncMessage);
    sendStatus();
  }

  if (millis() - lastHeartbeatMs >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeatMs = millis();
    sendStatus();
  }

  if (millis() - lastServerStatusMs >= SERVER_STATUS_REFRESH_MS) {
    lastServerStatusMs = millis();
    lastRssiPercent = lora.rssiPercent();
  }

  if (millis() - lastDisplayUpdateMs >= DISPLAY_REFRESH_MS) {
    lastDisplayUpdateMs = millis();
    drawDisplay();
  }

  forceLedsOff();
  delay(5);
}