/**
 * respawn_station.ino
 * ─────────────────────────────────────────────────────────────────────────────
 * AOJ Command OS — Respawn Station Prop Firmware
 *
 * Boards: Heltec V2, Heltec V3, generic ESP32 with SX1262/SX1276
 *
 * What this prop does:
 *   • Players press the big RESPAWN button to request a respawn.
 *   • The station reports the event to the server (LoRa + optional WiFi).
 *   • A configurable cooldown prevents rapid re-presses (RESPAWN_COOLDOWN_MS).
 *   • The server can restrict to RED-only, BLUE-only, or ALL teams via SET_TEAM.
 *   • Optional respawn count limit — server can set via SET_RESPAWN_COUNT.
 *   • LED/NeoPixel shows station team colour + ready/cooldown state.
 *   • A "READY" indicator (green LED or beep pattern) lets players know
 *     when they can spawn again.
 *
 * Hardware connections (all configurable below):
 *   BTN_RESPAWN_PIN  — large respawn button (INPUT_PULLUP, LOW = pressed)
 *   LED_READY_PIN    — green "ready to respawn" indicator
 *   LED_TEAM_PIN     — team colour LED (red or blue depending on assigned team)
 *   LED_DISABLED_PIN — red "station disabled" indicator
 *   BUZZER_PIN       — buzzer for confirmation beep
 *   NEOPIXEL_PIN     — NeoPixel data pin (set NEOPIXEL_COUNT > 0 to use)
 *
 * Server commands:
 *   ENABLE              — open for all teams (clears team restriction)
 *   DISABLE             — no respawns accepted
 *   SET_TEAM VALUE      — restrict to RED | BLUE | ALL
 *   SET_RESPAWN_COUNT V — set max remaining respawns (0 = unlimited)
 *   RESET               — enable + reset count
 *   STATUS_REQUEST      — send status heartbeat
 *
 * Events sent to server:
 *   STATUS              — heartbeat
 *   RESPAWN VALUE=TEAM:remaining_count
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// BOARD — uncomment exactly ONE
// ─────────────────────────────────────────────────────────────────────────────
// #define BOARD_HELTEC_V2
#define BOARD_HELTEC_V3
// #define BOARD_ESP32_GENERIC

// ─────────────────────────────────────────────────────────────────────────────
// IDENTITY
// ─────────────────────────────────────────────────────────────────────────────
#define DEVICE_ID   "RESPAWN-01"
#define PROP_TYPE   "Respawn"
#define FW_VERSION  "1.0.0"

// ─────────────────────────────────────────────────────────────────────────────
// WIFI (optional)
// ─────────────────────────────────────────────────────────────────────────────
#define USE_WIFI    0
#define WIFI_SSID   "AOJ_Server"
#define WIFI_PASS   "AOJ2023"
#define SERVER_URL  "http://192.168.1.100:8000"
#define PROP_TOKEN  ""

// ─────────────────────────────────────────────────────────────────────────────
// HARDWARE PINS
// ─────────────────────────────────────────────────────────────────────────────
#define BTN_RESPAWN_PIN   32    // respawn button (INPUT_PULLUP, LOW = pressed)
#define LED_READY_PIN     25    // green: station ready
#define LED_TEAM_PIN      26    // team colour indicator
#define LED_DISABLED_PIN  27    // red: station offline / disabled
#define BUZZER_PIN        14

#define NEOPIXEL_PIN      4
#define NEOPIXEL_COUNT    0     // set > 0 to use NeoPixels

// ─────────────────────────────────────────────────────────────────────────────
// GAME CONFIG
// ─────────────────────────────────────────────────────────────────────────────
#define RESPAWN_COOLDOWN_MS    5000    // ms between allowed respawns at this station
#define DEFAULT_MAX_RESPAWNS   0       // 0 = unlimited
#define HEARTBEAT_INTERVAL_MS  30000

// ─────────────────────────────────────────────────────────────────────────────
// Station team assignment — determines which team can use this station.
// Can be overridden at runtime via SET_TEAM command.
// Values: "ALL", "RED", "BLUE"
// ─────────────────────────────────────────────────────────────────────────────
#define DEFAULT_TEAM  "ALL"

// ─────────────────────────────────────────────────────────────────────────────
// Includes
// ─────────────────────────────────────────────────────────────────────────────
#include <AOJ_Core.h>

#if NEOPIXEL_COUNT > 0
  #include <Adafruit_NeoPixel.h>
  Adafruit_NeoPixel pixels(NEOPIXEL_COUNT, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
#endif

// ─────────────────────────────────────────────────────────────────────────────
// Objects
// ─────────────────────────────────────────────────────────────────────────────
AojLoRa lora;
AojWiFi wifi;

// ─────────────────────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────────────────────
enum StationState { STATION_DISABLED, STATION_READY, STATION_COOLDOWN };

StationState stationState  = STATION_DISABLED;
String       assignedTeam  = DEFAULT_TEAM;  // "ALL" | "RED" | "BLUE"
int          maxRespawns   = DEFAULT_MAX_RESPAWNS;
int          spawnCount    = 0;             // total spawns issued this game

unsigned long lastRespawnMs = 0;
unsigned long lastHeartbeat = 0;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const char *stationStatusLabel() {
  switch (stationState) {
    case STATION_READY:    return "online";
    case STATION_COOLDOWN: return "online";
    default:               return "disarmed";
  }
}

void sendFrame(const String &cmd, const String &val, const String &mid) {
  String frame = aojBuildFrame(DEVICE_ID, cmd, val, mid);
  lora.send(frame);
}

void sendAck(const String &mid, const String &val = "OK") {
  sendFrame("ACK", val, mid);
}

void sendStatus() {
  int battery  = aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
  int rssi     = lora.rssiPercent();
  int remaining = (maxRespawns > 0) ? (maxRespawns - spawnCount) : -1;
  // STATUS value: state:team:remaining:battery:rssi:type
  String value = String(stationStatusLabel()) + ":" +
                 assignedTeam + ":" +
                 String(remaining) + ":" +
                 String(battery) + ":" +
                 String(rssi) + ":" +
                 PROP_TYPE;
  sendFrame("STATUS", value, aojGenerateMessageId());
  wifi.reportStatus(DEVICE_ID, stationStatusLabel(), battery, rssi, FW_VERSION);
}

void beep(int ms = 80) {
  digitalWrite(BUZZER_PIN, HIGH); delay(ms); digitalWrite(BUZZER_PIN, LOW);
}

void respawnBeep() {
  // Two-tone: short low + long high
  beep(100); delay(50); beep(300);
}

// ─────────────────────────────────────────────────────────────────────────────
// Visual output
// ─────────────────────────────────────────────────────────────────────────────

void updateLeds() {
#if NEOPIXEL_COUNT > 0
  uint32_t color;
  if (stationState == STATION_DISABLED) {
    color = pixels.Color(50, 0, 0);            // dim red = offline
  } else if (stationState == STATION_COOLDOWN) {
    color = pixels.Color(50, 50, 0);           // yellow = cooldown
  } else {
    // Ready — show team colour
    if (assignedTeam == "RED")       color = pixels.Color(0, 180, 0);  // green = ready (neutral glow)
    else if (assignedTeam == "BLUE") color = pixels.Color(0, 180, 0);
    else                             color = pixels.Color(0, 180, 0);  // green = open
  }
  pixels.fill(color); pixels.show();
#else
  bool disabled = (stationState == STATION_DISABLED);
  bool ready    = (stationState == STATION_READY);
  bool cooldown = (stationState == STATION_COOLDOWN);

  digitalWrite(LED_DISABLED_PIN, disabled ? HIGH : LOW);
  digitalWrite(LED_READY_PIN,    ready    ? HIGH : LOW);
  // Team LED pulses during cooldown, steady when ready
  digitalWrite(LED_TEAM_PIN, (ready || cooldown) ? HIGH : LOW);
#endif
}

// ─────────────────────────────────────────────────────────────────────────────
// Command handler
// ─────────────────────────────────────────────────────────────────────────────

void handleCommand(const AOJFrame &f) {
  if (f.command == "ENABLE") {
    assignedTeam = "ALL";
    stationState = STATION_READY;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "DISABLE") {
    stationState = STATION_DISABLED;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "RESET") {
    stationState = STATION_READY;
    assignedTeam = DEFAULT_TEAM;
    spawnCount   = 0;
    maxRespawns  = DEFAULT_MAX_RESPAWNS;
    lastRespawnMs = 0;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "SET_TEAM") {
    if (f.value == "RED" || f.value == "BLUE" || f.value == "ALL") {
      assignedTeam = f.value;
    }
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "SET_RESPAWN_COUNT") {
    int val = f.value.toInt();
    if (val >= 0) { maxRespawns = val; spawnCount = 0; }
    sendAck(f.messageId);
  }
  else if (f.command == "ARM") {
    stationState = STATION_READY;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "DISARM") {
    stationState = STATION_DISABLED;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "STATUS_REQUEST") {
    sendAck(f.messageId);
    sendStatus();
  }
  else {
    sendAck(f.messageId, "UNKNOWN");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Respawn event
// ─────────────────────────────────────────────────────────────────────────────

void issueRespawn() {
  spawnCount++;
  int remaining = (maxRespawns > 0) ? (maxRespawns - spawnCount) : -1;

  Serial.print("[RESPAWN] Issued — team: "); Serial.print(assignedTeam);
  Serial.print("  total: "); Serial.println(spawnCount);

  String value = assignedTeam + ":" + String(remaining);
  sendFrame("RESPAWN", value, aojGenerateMessageId());

  respawnBeep();
  lastRespawnMs = millis();
  stationState  = STATION_COOLDOWN;
  updateLeds();

  // If we have hit the max respawn count, disable the station.
  if (maxRespawns > 0 && spawnCount >= maxRespawns) {
    stationState = STATION_DISABLED;
    updateLeds();
    Serial.println("[RESPAWN] Max respawns reached — station disabled");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// setup()
// ─────────────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[AOJ] Respawn station — " DEVICE_ID);

  pinMode(BUZZER_PIN,      OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  pinMode(LED_READY_PIN,   OUTPUT);
  pinMode(LED_TEAM_PIN,    OUTPUT);
  pinMode(LED_DISABLED_PIN,OUTPUT);
  pinMode(BTN_RESPAWN_PIN, INPUT_PULLUP);

#if NEOPIXEL_COUNT > 0
  pixels.begin(); pixels.setBrightness(80);
#endif

  if (!lora.begin()) {
    Serial.println("[AOJ] LoRa init failed — halting");
    while (true) delay(1000);
  }

  wifi.begin(WIFI_SSID, WIFI_PASS, SERVER_URL, PROP_TOKEN);

  updateLeds();
  sendStatus();
  lastHeartbeat = millis();
  Serial.println("[AOJ] Ready");
}

// ─────────────────────────────────────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────────────────────────────────────

void loop() {
  // ── LoRa receive ─────────────────────────────────────────────────────────
  if (lora.available()) {
    String raw = lora.read();
    if (raw.length() > 0) {
      AOJFrame f = aojParseFrame(raw);
      if (f.valid && (f.deviceId == DEVICE_ID || f.deviceId == "*")) {
        handleCommand(f);
      }
    }
  }

  // ── Cooldown → ready transition ──────────────────────────────────────────
  if (stationState == STATION_COOLDOWN) {
    if (millis() - lastRespawnMs >= RESPAWN_COOLDOWN_MS) {
      stationState = STATION_READY;
      updateLeds();
    }
  }

  // ── Respawn button ────────────────────────────────────────────────────────
  if (stationState == STATION_READY) {
    static bool lastBtnState = HIGH;
    bool btnState = digitalRead(BTN_RESPAWN_PIN);
    // Trigger on falling edge (button press)
    if (btnState == LOW && lastBtnState == HIGH) {
      issueRespawn();
    }
    lastBtnState = btnState;
  }

  // ── Heartbeat ─────────────────────────────────────────────────────────────
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = millis();
    sendStatus();
  }
}
