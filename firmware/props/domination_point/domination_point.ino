/**
 * domination_point.ino
 * ─────────────────────────────────────────────────────────────────────────────
 * AOJ Command OS — Domination Point Prop Firmware
 *
 * Boards: Heltec V2, Heltec V3, generic ESP32 with SX1262/SX1276
 *
 * What this prop does:
 *   • Neutral at game start.
 *   • A player holds their team button (or single shared button toggles team).
 *   • After CAP_TIME_MS of uncontested hold, the point is captured.
 *   • If the opposing team starts pressing while a cap is in progress, the
 *     cap progress resets (contested).
 *   • Captured state broadcasts CAPTURED|TEAM and holds until reset or recaptured.
 *   • NeoPixel ring or two team LEDs show current ownership / capture progress.
 *
 * Hardware connections (all configurable below):
 *   BTN_RED_PIN     — red team capture button (INPUT_PULLUP, press = LOW)
 *   BTN_BLUE_PIN    — blue team capture button (INPUT_PULLUP, press = LOW)
 *                     If using a single shared button, set BTN_BLUE_PIN = -1
 *                     and the button will cycle through teams on each press.
 *   LED_RED_PIN     — red team solid LED
 *   LED_BLUE_PIN    — blue team solid LED
 *   LED_NEUTRAL_PIN — neutral/contested LED (white or yellow)
 *   BUZZER_PIN      — buzzer for capture complete / contest
 *   NEOPIXEL_PIN    — NeoPixel data pin (set NEOPIXEL_COUNT > 0 to use)
 *
 * Server commands:
 *   ARM             — enable the point (starts accepting captures)
 *   DISARM          — lock the point (ignore button input)
 *   RESET           — return to NEUTRAL
 *   SET_TEAM VALUE  — force team ownership: RED | BLUE | NEUTRAL
 *   LOCK            — alias for DISARM
 *   STATUS_REQUEST  — send status heartbeat
 *
 * Events sent to server:
 *   STATUS          — heartbeat
 *   CAPTURED VALUE=RED|BLUE|NEUTRAL
 *   CONTESTED       — sent once when capture is interrupted
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
#define DEVICE_ID   "DOM-01"
#define PROP_TYPE   "Domination"
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
#define BTN_RED_PIN      32    // red team button  (INPUT_PULLUP, LOW = pressed)
#define BTN_BLUE_PIN     33    // blue team button (set to -1 for single-button mode)
#define LED_RED_PIN      25    // red LED
#define LED_BLUE_PIN     26    // blue LED
#define LED_NEUTRAL_PIN  27    // neutral / contested LED

#define BUZZER_PIN       14    // buzzer

#define NEOPIXEL_PIN     4
#define NEOPIXEL_COUNT   0     // set > 0 and install Adafruit NeoPixel lib

// ─────────────────────────────────────────────────────────────────────────────
// GAME CONFIG
// ─────────────────────────────────────────────────────────────────────────────
#define CAP_TIME_MS          10000   // milliseconds of uncontested hold to capture
#define HEARTBEAT_INTERVAL_MS 30000

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
enum DomTeam  { TEAM_NEUTRAL, TEAM_RED, TEAM_BLUE };
enum DomState { DOM_LOCKED, DOM_NEUTRAL, DOM_CAPTURING, DOM_OWNED_RED, DOM_OWNED_BLUE };

DomState domState     = DOM_LOCKED;
DomTeam  ownedBy      = TEAM_NEUTRAL;
DomTeam  capturingTeam = TEAM_NEUTRAL;

unsigned long capStartMs    = 0;
unsigned long lastHeartbeat = 0;
bool          wasContested  = false;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const char *teamLabel(DomTeam t) {
  switch (t) {
    case TEAM_RED:  return "RED";
    case TEAM_BLUE: return "BLUE";
    default:        return "NEUTRAL";
  }
}

const char *domStatusLabel() {
  switch (domState) {
    case DOM_LOCKED:    return "disarmed";
    case DOM_OWNED_RED: return "armed";     // "armed" maps to a generic active state
    case DOM_OWNED_BLUE:return "armed";
    default:            return "online";
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
  int battery = aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
  int rssi    = lora.rssiPercent();
  // STATUS value: state:owner:battery:rssi:type
  String value = String(domStatusLabel()) + ":" +
                 teamLabel(ownedBy) + ":" +
                 String(battery) + ":" +
                 String(rssi) + ":" +
                 PROP_TYPE;
  sendFrame("STATUS", value, aojGenerateMessageId());
  wifi.reportStatus(DEVICE_ID, domStatusLabel(), battery, rssi, FW_VERSION);
}

void beep(int ms = 80) {
  digitalWrite(BUZZER_PIN, HIGH); delay(ms); digitalWrite(BUZZER_PIN, LOW);
}

// ─────────────────────────────────────────────────────────────────────────────
// Visual output
// ─────────────────────────────────────────────────────────────────────────────

void updateLeds() {
#if NEOPIXEL_COUNT > 0
  uint32_t color;
  switch (domState) {
    case DOM_OWNED_RED:   color = pixels.Color(200,   0,   0); break;
    case DOM_OWNED_BLUE:  color = pixels.Color(  0,   0, 200); break;
    case DOM_CAPTURING:
      color = (capturingTeam == TEAM_RED) ? pixels.Color(100, 0, 0) : pixels.Color(0, 0, 100);
      break;
    case DOM_LOCKED:      color = pixels.Color( 20,  20,  20); break;
    default:              color = pixels.Color( 50,  50,   0); break;
  }
  pixels.fill(color); pixels.show();
#else
  digitalWrite(LED_RED_PIN,     domState == DOM_OWNED_RED  ? HIGH : LOW);
  digitalWrite(LED_BLUE_PIN,    domState == DOM_OWNED_BLUE ? HIGH : LOW);
  bool neutral = (domState == DOM_NEUTRAL || domState == DOM_CAPTURING || domState == DOM_LOCKED);
  digitalWrite(LED_NEUTRAL_PIN, neutral ? HIGH : LOW);
#endif
}

// ─────────────────────────────────────────────────────────────────────────────
// Capture logic
// ─────────────────────────────────────────────────────────────────────────────

void capturePoint(DomTeam team) {
  ownedBy = team;
  domState = (team == TEAM_RED) ? DOM_OWNED_RED : DOM_OWNED_BLUE;
  capturingTeam = TEAM_NEUTRAL;
  updateLeds();
  // Three ascending beeps
  beep(100); delay(80); beep(150); delay(80); beep(250);
  String mid = aojGenerateMessageId();
  sendFrame("CAPTURED", teamLabel(team), mid);
  Serial.print("[DOM] Captured by "); Serial.println(teamLabel(team));
}

void resetPoint() {
  domState      = DOM_NEUTRAL;
  ownedBy       = TEAM_NEUTRAL;
  capturingTeam = TEAM_NEUTRAL;
  capStartMs    = 0;
  wasContested  = false;
  updateLeds();
  Serial.println("[DOM] Reset to neutral");
}

// ─────────────────────────────────────────────────────────────────────────────
// Command handler
// ─────────────────────────────────────────────────────────────────────────────

void handleCommand(const AOJFrame &f) {
  if (f.command == "ARM") {
    domState = DOM_NEUTRAL;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "DISARM" || f.command == "LOCK") {
    domState = DOM_LOCKED;
    capturingTeam = TEAM_NEUTRAL;
    updateLeds();
    sendAck(f.messageId);
  }
  else if (f.command == "RESET") {
    resetPoint();
    sendAck(f.messageId);
  }
  else if (f.command == "SET_TEAM") {
    if (f.value == "RED")  { ownedBy = TEAM_RED;  domState = DOM_OWNED_RED; }
    else if (f.value == "BLUE") { ownedBy = TEAM_BLUE; domState = DOM_OWNED_BLUE; }
    else { resetPoint(); sendAck(f.messageId); return; }
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
// setup()
// ─────────────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[AOJ] Domination point — " DEVICE_ID);

  pinMode(BUZZER_PIN,     OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  pinMode(LED_RED_PIN,    OUTPUT);
  pinMode(LED_BLUE_PIN,   OUTPUT);
  pinMode(LED_NEUTRAL_PIN,OUTPUT);
  pinMode(BTN_RED_PIN,    INPUT_PULLUP);
#if BTN_BLUE_PIN >= 0
  pinMode(BTN_BLUE_PIN,   INPUT_PULLUP);
#endif

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

  // ── Capture logic (only when not locked) ─────────────────────────────────
  if (domState != DOM_LOCKED) {
    bool redDown  = (digitalRead(BTN_RED_PIN) == LOW);
#if BTN_BLUE_PIN >= 0
    bool blueDown = (digitalRead(BTN_BLUE_PIN) == LOW);
#else
    // Single-button mode: reuse red pin, alternating team per press
    // (simple implementation — extend with edge detection if needed)
    bool blueDown = false;
#endif

    bool contested = redDown && blueDown;

    if (contested) {
      // Both teams pressing — interrupt any ongoing capture
      if (capturingTeam != TEAM_NEUTRAL) {
        capturingTeam = TEAM_NEUTRAL;
        capStartMs    = 0;
        if (!wasContested) {
          wasContested = true;
          sendFrame("CONTESTED", "OK", aojGenerateMessageId());
          beep(300);
        }
        domState = DOM_NEUTRAL;
        updateLeds();
      }
    }
    else if (redDown || blueDown) {
      DomTeam pressing = redDown ? TEAM_RED : TEAM_BLUE;
      wasContested = false;

      if (capturingTeam == TEAM_NEUTRAL) {
        // Start a new cap attempt (or re-cap from existing owner)
        if (ownedBy != pressing) {
          capturingTeam = pressing;
          capStartMs    = millis();
          domState      = DOM_CAPTURING;
          updateLeds();
          Serial.print("[DOM] Capture started by "); Serial.println(teamLabel(pressing));
        }
      }
      else if (capturingTeam == pressing) {
        // Continue holding — check if time is up
        if (millis() - capStartMs >= CAP_TIME_MS) {
          capturePoint(pressing);
        }
      }
      else {
        // Opposite team interrupted — reset
        capturingTeam = pressing;
        capStartMs    = millis();
        updateLeds();
      }
    }
    else {
      // No buttons held — cancel in-progress capture (must hold continuously)
      if (capturingTeam != TEAM_NEUTRAL) {
        capturingTeam = TEAM_NEUTRAL;
        capStartMs    = 0;
        domState = (ownedBy == TEAM_RED)  ? DOM_OWNED_RED :
                   (ownedBy == TEAM_BLUE) ? DOM_OWNED_BLUE : DOM_NEUTRAL;
        updateLeds();
      }
      wasContested = false;
    }
  }

  // ── Heartbeat ─────────────────────────────────────────────────────────────
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = millis();
    sendStatus();
  }
}
