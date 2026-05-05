/**
 * prop_bomb.ino
 * ─────────────────────────────────────────────────────────────────────────────
 * AOJ Command OS — Bomb Prop Firmware
 *
 * Boards: Heltec V2, Heltec V3, generic ESP32 with SX1262/SX1276
 *
 * What this prop does:
 *   • Waits in IDLE state until the server sends ARM.
 *   • ARM starts a countdown timer (default 5 minutes, server-configurable).
 *   • A player must hold the DEFUSE button for DEFUSE_HOLD_MS to defuse.
 *   • If the countdown hits zero before defuse → EXPLODED event sent.
 *   • DISARM command from server also defuses immediately (admin override).
 *   • RESET returns the bomb to IDLE.
 *
 * Hardware connections (all configurable below):
 *   BUZZER_PIN   — piezo buzzer (active HIGH)
 *   LED_RED_PIN  — status LED red   (armed / exploded)
 *   LED_GREEN_PIN— status LED green (idle / defused)
 *   DEFUSE_BTN   — defuse button (INPUT_PULLUP, active LOW)
 *
 * NeoPixel strip (optional) — set NEOPIXEL_PIN to your data pin, NEOPIXEL_COUNT
 * to number of pixels.  Requires Adafruit NeoPixel library.
 *
 * Server commands handled:
 *   ARM [VALUE=seconds]   — arms the bomb; optionally sets timer
 *   DISARM                — immediately defuses
 *   RESET                 — returns to idle, clears timer
 *   STATUS_REQUEST        — sends status heartbeat immediately
 *   SET_TIMER VALUE=secs  — change timer duration while idle
 *
 * Events sent to server:
 *   STATUS  — heartbeat every HEARTBEAT_INTERVAL_MS
 *   EXPLODED
 *   DEFUSED
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ─────────────────────────────────────────────────────────────────────────────
// BOARD — uncomment exactly ONE
// ─────────────────────────────────────────────────────────────────────────────
// #define BOARD_HELTEC_V2
#define BOARD_HELTEC_V3
// #define BOARD_ESP32_GENERIC

// ─────────────────────────────────────────────────────────────────────────────
// IDENTITY — must match the record in AOJ Prop Network
// ─────────────────────────────────────────────────────────────────────────────
#define DEVICE_ID   "BD-001"
#define PROP_TYPE   "Bomb"
#define FW_VERSION  "1.3.8"

// ─────────────────────────────────────────────────────────────────────────────
// WIFI (optional)
// Set USE_WIFI 1 to enable HTTP status reporting over WiFi.
// ─────────────────────────────────────────────────────────────────────────────
#define USE_WIFI    0
#define WIFI_SSID   "AOJ_Server"
#define WIFI_PASS   "AOJ2023"
#define SERVER_URL  "http://192.168.1.100:8000"   // AOJ backend IP
#define PROP_TOKEN  ""                             // from AOJ admin → Prop Network

// ─────────────────────────────────────────────────────────────────────────────
// HARDWARE PINS — adjust for your wiring
// ─────────────────────────────────────────────────────────────────────────────
#define BUZZER_PIN       25    // piezo buzzer (active HIGH)
#define LED_RED_PIN      26    // red indicator LED
#define LED_GREEN_PIN    27    // green indicator LED
#define DEFUSE_BTN       32    // defuse button (INPUT_PULLUP, press = LOW)

// NeoPixel strip (set COUNT to 0 to disable)
#define NEOPIXEL_PIN     33
#define NEOPIXEL_COUNT   0     // set >0 to use NeoPixels instead of simple LEDs

// ─────────────────────────────────────────────────────────────────────────────
// GAME CONFIG
// ─────────────────────────────────────────────────────────────────────────────
#define DEFAULT_TIMER_SECS  300    // 5-minute bomb by default
#define DEFUSE_HOLD_MS      3000   // hold defuse button this long to defuse
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
enum BombState { BOMB_IDLE, BOMB_ARMED, BOMB_DEFUSED, BOMB_EXPLODED };
BombState bombState = BOMB_IDLE;

unsigned long timerDurationMs = (unsigned long)DEFAULT_TIMER_SECS * 1000UL;
unsigned long armedAtMs       = 0;
unsigned long defusePressedAt = 0;
bool          defuseHeld      = false;
unsigned long lastHeartbeat   = 0;

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const char *bombStateLabel() {
  switch (bombState) {
    case BOMB_ARMED:    return "armed";
    case BOMB_DEFUSED:  return "disarmed";
    case BOMB_EXPLODED: return "alarm";
    default:            return "online";
  }
}

void sendFrame(const String &cmd, const String &val, const String &mid) {
  String frame = aojBuildFrame(DEVICE_ID, cmd, val, mid);
  lora.send(frame);
}

void sendAck(const String &messageId, const String &val = "OK") {
  sendFrame("ACK", val, messageId);
}

void sendStatus() {
  int battery = aojReadBattery(BATTERY_ADC_PIN, BATTERY_FULL_MV, BATTERY_EMPTY_MV);
  int rssi    = lora.rssiPercent();
  String value = String(bombStateLabel()) + ":" +
                 String(battery) + ":" +
                 String(rssi) + ":" +
                 PROP_TYPE;
  sendFrame("STATUS", value, aojGenerateMessageId());

  // Also report via WiFi if available.
  wifi.reportStatus(DEVICE_ID, bombStateLabel(), battery, rssi, FW_VERSION);
}

// ─────────────────────────────────────────────────────────────────────────────
// LED / buzzer helpers
// ─────────────────────────────────────────────────────────────────────────────

void setLeds(bool red, bool green) {
#if NEOPIXEL_COUNT > 0
  uint32_t color = red   ? pixels.Color(200, 0, 0) :
                   green ? pixels.Color(0, 200, 0) :
                           pixels.Color(0, 0, 0);
  pixels.fill(color);
  pixels.show();
#else
  digitalWrite(LED_RED_PIN,   red   ? HIGH : LOW);
  digitalWrite(LED_GREEN_PIN, green ? HIGH : LOW);
#endif
}

// Short beep — called on arm tick and events.
void beep(int durationMs = 80) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(durationMs);
  digitalWrite(BUZZER_PIN, LOW);
}

void alarmBuzz() {
  // Rapid triple beep for explosion / alert
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH); delay(150);
    digitalWrite(BUZZER_PIN, LOW);  delay(80);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bomb actions
// ─────────────────────────────────────────────────────────────────────────────

void armBomb(unsigned long durationMs) {
  timerDurationMs = durationMs;
  armedAtMs       = millis();
  bombState       = BOMB_ARMED;
  setLeds(true, false);
  beep(200);
  Serial.print("[BOMB] Armed — timer: "); Serial.print(durationMs / 1000); Serial.println("s");
}

void defuseBomb() {
  bombState = BOMB_DEFUSED;
  setLeds(false, true);
  beep(500);
  String mid = aojGenerateMessageId();
  sendFrame("DEFUSED", "OK", mid);
  Serial.println("[BOMB] Defused");
}

void explodeBomb() {
  bombState = BOMB_EXPLODED;
  setLeds(true, false);
  alarmBuzz();
  String mid = aojGenerateMessageId();
  sendFrame("EXPLODED", "OK", mid);
  Serial.println("[BOMB] EXPLODED");
}

void resetBomb() {
  bombState     = BOMB_IDLE;
  defuseHeld    = false;
  defusePressedAt = 0;
  setLeds(false, true);
  Serial.println("[BOMB] Reset to idle");
}

// ─────────────────────────────────────────────────────────────────────────────
// Command handler
// ─────────────────────────────────────────────────────────────────────────────

void handleCommand(const AOJFrame &f) {
  if (f.command == "ARM") {
    unsigned long duration = timerDurationMs;
    if (f.value.length() > 0) {
      long secs = f.value.toInt();
      if (secs > 0) duration = (unsigned long)secs * 1000UL;
    }
    armBomb(duration);
    sendAck(f.messageId);
  }
  else if (f.command == "DISARM") {
    if (bombState == BOMB_ARMED) defuseBomb();
    sendAck(f.messageId);
  }
  else if (f.command == "RESET") {
    resetBomb();
    sendAck(f.messageId);
  }
  else if (f.command == "SET_TIMER") {
    if (bombState == BOMB_IDLE) {
      long secs = f.value.toInt();
      if (secs > 0) timerDurationMs = (unsigned long)secs * 1000UL;
    }
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
  Serial.println("\n[AOJ] Bomb prop — " DEVICE_ID);

  // GPIO
  pinMode(BUZZER_PIN,    OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  pinMode(LED_RED_PIN,   OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(DEFUSE_BTN,    INPUT_PULLUP);

#if NEOPIXEL_COUNT > 0
  pixels.begin();
  pixels.setBrightness(80);
#endif

  // LoRa
  if (!lora.begin()) {
    Serial.println("[AOJ] LoRa init failed — halting");
    while (true) delay(1000);
  }

  // WiFi (compiled away if USE_WIFI 0)
  wifi.begin(WIFI_SSID, WIFI_PASS, SERVER_URL, PROP_TOKEN);

  resetBomb();
  sendStatus();
  lastHeartbeat = millis();
  Serial.println("[AOJ] Ready");
}

// ─────────────────────────────────────────────────────────────────────────────
// loop()
// ─────────────────────────────────────────────────────────────────────────────

void loop() {
  // ── LoRa receive ────────────────────────────────────────────────────────
  if (lora.available()) {
    String raw = lora.read();
    if (raw.length() > 0) {
      AOJFrame f = aojParseFrame(raw);
      if (f.valid && (f.deviceId == DEVICE_ID || f.deviceId == "*")) {
        handleCommand(f);
      }
    }
  }

  // ── Bomb countdown ──────────────────────────────────────────────────────
  if (bombState == BOMB_ARMED) {
    unsigned long elapsed = millis() - armedAtMs;
    unsigned long remaining = (elapsed < timerDurationMs) ? timerDurationMs - elapsed : 0;

    // Countdown beep every second while armed
    static unsigned long lastBeepMs = 0;
    if (millis() - lastBeepMs >= 1000) {
      lastBeepMs = millis();
      beep(50);  // 50ms tick; gets faster in last 10s
    }

    // Faster beeps in final 10 seconds
    if (remaining > 0 && remaining <= 10000) {
      if (millis() - lastBeepMs >= 300) {
        lastBeepMs = millis();
        beep(40);
      }
    }

    if (remaining == 0) {
      explodeBomb();
    }
  }

  // ── Defuse button ────────────────────────────────────────────────────────
  if (bombState == BOMB_ARMED) {
    bool btnDown = (digitalRead(DEFUSE_BTN) == LOW);
    if (btnDown && !defuseHeld) {
      defusePressedAt = millis();
      defuseHeld = true;
    }
    if (!btnDown) {
      defuseHeld = false;
      defusePressedAt = 0;
    }
    if (defuseHeld && (millis() - defusePressedAt >= DEFUSE_HOLD_MS)) {
      defuseBomb();
      defuseHeld = false;
    }
  }

  // ── Heartbeat ────────────────────────────────────────────────────────────
  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
    lastHeartbeat = millis();
    sendStatus();
  }
}
