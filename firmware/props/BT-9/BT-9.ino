/*
  CERBERUS_CORE.ino
  =============================================================================
  AOJ CERBERUS OS — Multi-Role Airsoft Objective Controller
  Board: Heltec WiFi LoRa 32 V3 / ESP32-S3 / SX1262

  Safe use:
  - Airsoft / toy objective prop only.
  - No ignition outputs.
  - No pyrotechnic outputs.
  - No real explosive functions.
  - All "payload", "mission fail", and "armed" language is for game immersion only.

  Hardware:
  - Heltec WiFi LoRa 32 V3
  - I2C OLED SSD1306 / SSD1309
  - I2C HT16K33 4-digit 7-segment display
  - 4x4 matrix keypad
  - Arming switch
  - Red momentary button
  - DFPlayer Mini + speaker
  - Active buzzer
  - Dummy prop loop / socket input

  Required Arduino libraries:
  - RadioLib
  - U8g2
  - Keypad
  - DFRobotDFPlayerMini
  - Adafruit GFX Library
  - Adafruit LED Backpack
  - Preferences
*/

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <Wire.h>
#include <SPI.h>
#include <RadioLib.h>
#include <U8g2lib.h>
#include <Keypad.h>
#include <DFRobotDFPlayerMini.h>
#include <Adafruit_GFX.h>
#include <Adafruit_LEDBackpack.h>

// =============================================================================
// IDENTITY
// =============================================================================

#define DEVICE_ID        "CERBERUS-01"
#define DEVICE_NAME      "CERBERUS CORE"
#define FW_VERSION       "2.0.0"

// =============================================================================
// WIFI AP
// =============================================================================

#define AP_SSID          "AOJ-CERBERUS-01"
#define AP_PASSWORD      "ChangeThisPassword83"

// =============================================================================
// LORA SECURITY / SETTINGS
// =============================================================================

#define LORA_SHARED_KEY  "AOJ_CHANGE_THIS_KEY"

// Japan commonly uses the 920 MHz band. Confirm the exact legal channel/frequency.
// Do not use 915.0 in Japan unless your equipment and local rules allow it.
#define LORA_FREQUENCY   923.0
#define LORA_BANDWIDTH   125.0
#define LORA_SF          9
#define LORA_CR          7
#define LORA_POWER       13

// Heltec WiFi LoRa 32 V3 SX1262 pins.
// Verify with your exact board revision.
#define PIN_LORA_SCK     9
#define PIN_LORA_MISO    11
#define PIN_LORA_MOSI    10
#define PIN_LORA_NSS     8
#define PIN_LORA_DIO1    14
#define PIN_LORA_RST     12
#define PIN_LORA_BUSY    13

// =============================================================================
// PIN MAP
// =============================================================================

#define PIN_I2C_SDA      17
#define PIN_I2C_SCL      18

#define PIN_BUZZER       47
#define PIN_ARM_SWITCH   33
#define PIN_RED_BUTTON   34
#define PIN_DUMMY_PROP   45

// Battery ADC is disabled by default because GPIO46 may not be a usable ADC pin
// on all ESP32-S3 boards. Set USE_BATTERY_ADC to 1 only after confirming your pin.
#define USE_BATTERY_ADC  0
#define PIN_BATTERY_ADC  46

#define PIN_MP3_RX       15    // ESP32 RX  <- DFPlayer TX
#define PIN_MP3_TX       16    // ESP32 TX  -> DFPlayer RX via ~1k resistor

// Keypad pins.
// Your original used GPIO 1,2,3,4 and 5,6,7,9.
// Keep if tested. Change if USB/boot/serial conflict appears.
static const byte KP_ROWS = 4;
static const byte KP_COLS = 4;

static byte kpRowPins[KP_ROWS] = { 1, 2, 3, 4 };
static byte kpColPins[KP_COLS] = { 5, 6, 7, 21 };

static char kpKeys[KP_ROWS][KP_COLS] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' }
};

// 7-segment I2C address
#define SEG7_ADDR        0x70

// =============================================================================
// TIMING
// =============================================================================

#define OLED_REFRESH_MS      120UL
#define SEG7_REFRESH_MS      120UL
#define HEARTBEAT_MS         15000UL
#define INPUT_TICK_MS        20UL
#define DUMMY_DEBOUNCE_MS    80UL
#define LORA_POLL_MS         30UL
#define WEB_TICK_MS          2UL

// =============================================================================
// OBJECTS
// =============================================================================

SX1262 radio = new Module(PIN_LORA_NSS, PIN_LORA_DIO1, PIN_LORA_RST, PIN_LORA_BUSY);

U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);
// For 2.42" SSD1309, comment the line above and use this:
// U8G2_SSD1309_128X64_NONAME0_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

Adafruit_7segment seg7 = Adafruit_7segment();

Keypad keypad = Keypad(makeKeymap(kpKeys), kpRowPins, kpColPins, KP_ROWS, KP_COLS);

HardwareSerial mp3Serial(1);
DFRobotDFPlayerMini mp3Player;

WebServer webServer(80);
Preferences prefs;

// =============================================================================
// ENUMS
// =============================================================================

enum ObjectiveTheme : uint8_t {
  THEME_PAYLOAD        = 0,
  THEME_GUIDANCE       = 1,
  THEME_CONTROLLER     = 2,
  THEME_REACTOR        = 3,
  THEME_DATA_TERMINAL  = 4
};

enum GameProfile : uint8_t {
  PROFILE_CUSTOM           = 0,
  PROFILE_SEARCH_DESTROY   = 1,
  PROFILE_MISSILE_GUIDANCE = 2,
  PROFILE_REACTOR_CORE     = 3,
  PROFILE_DEADMAN_SWITCH   = 4,
  PROFILE_PAYLOAD_LINK     = 5
};

enum ArmMethod : uint8_t {
  ARM_HOLD_RED             = 0,
  ARM_ENTER_CODE           = 1,
  ARM_SWITCH_AND_BUTTON    = 2,
  ARM_DUMMY_AND_CODE       = 3
};

enum DisarmMethod : uint8_t {
  DISARM_HOLD_RED          = 0,
  DISARM_ENTER_CODE        = 1,
  DISARM_SWITCH_AND_BUTTON = 2,
  DISARM_REMOVE_DUMMY      = 3,
  DISARM_MULTI_STAGE       = 4
};

enum WrongCodePenalty : uint8_t {
  PENALTY_BEEP_ONLY        = 0,
  PENALTY_SUBTRACT_TIME    = 1,
  PENALTY_TEMP_LOCKOUT     = 2,
  PENALTY_FORCE_PHASE_2    = 3,
  PENALTY_FORCE_PHASE_3    = 4
};

enum DeviceState : uint8_t {
  STATE_BOOTING            = 0,
  STATE_IDLE               = 1,
  STATE_WAIT_PREREQ        = 2,
  STATE_STANDBY            = 3,
  STATE_ARMING             = 4,
  STATE_ACTIVE             = 5,
  STATE_DISARMING          = 6,
  STATE_DISARMED           = 7,
  STATE_MISSION_FAILED     = 8,
  STATE_LOCKED_OUT         = 9,
  STATE_ADMIN_DISABLED     = 10
};

enum DevicePhase : uint8_t {
  PHASE_SAFE               = 0,
  PHASE_1                  = 1,
  PHASE_2                  = 2,
  PHASE_3                  = 3
};

enum BeepPattern : uint8_t {
  BEEP_NONE                = 0,
  BEEP_BOOT                = 1,
  BEEP_CLICK               = 2,
  BEEP_ARMED              = 3,
  BEEP_ERROR              = 4,
  BEEP_SUCCESS            = 5,
  BEEP_WARNING            = 6,
  BEEP_FAIL               = 7
};

// =============================================================================
// MP3 TRACKS
// =============================================================================

#define TRACK_BOOT             1
#define TRACK_ARMED_PAYLOAD    2
#define TRACK_ARMED_GUIDANCE   3
#define TRACK_ARMED_CONTROLLER 4
#define TRACK_PHASE2           5
#define TRACK_PHASE3           6
#define TRACK_MISSION_FAILED   7
#define TRACK_GUIDANCE_LOCK    8
#define TRACK_CONTROLLER_FIRE  9
#define TRACK_DISARMED         10
#define TRACK_WRONG_CODE       11
#define TRACK_LOCKOUT          12
#define TRACK_PREREQ_MET       13
#define TRACK_ADMIN_DISABLED   14
#define TRACK_ARMING_INIT      15
#define TRACK_POWER_LOW        16

// =============================================================================
// CONFIGURATION
// =============================================================================

struct CerberusConfig {
  GameProfile profile;
  ObjectiveTheme theme;

  ArmMethod armMethod;
  DisarmMethod disarmMethod;
  WrongCodePenalty wrongPenalty;

  char armCode[16];
  char disarmCode[16];
  char adminPin[12];

  uint32_t timerSeconds;
  uint32_t holdRedMs;

  bool requireDummyToArm;
  bool requireDummyToDisarm;
  bool alertIfDummyRemovedActive;

  bool lockoutOnWrongCode;
  int maxWrongAttempts;
  int lockoutDurationSecs;
  int wrongCodeTimePenaltySecs;

  uint8_t phase2Percent;
  uint8_t phase3Percent;

  bool enableAudio;
  int mp3Volume;

  bool enableLoRa;
  bool requireLoraKey;
};

CerberusConfig cfg;

// =============================================================================
// RUNTIME STATE
// =============================================================================

DeviceState deviceState = STATE_BOOTING;
DevicePhase devicePhase = PHASE_SAFE;
DevicePhase lastAnnouncedPhase = PHASE_SAFE;

unsigned long stateEnteredMs = 0;
unsigned long timerEndMs = 0;
long timerRemainMs = 0;

unsigned long actionStartMs = 0;
bool actionActive = false;

String codeInput = "";
int wrongAttempts = 0;

unsigned long lockoutEndMs = 0;

bool dummyConnected = false;
bool dummyLastRaw = false;
bool dummyStable = false;
unsigned long dummyChangedMs = 0;

bool mp3Ready = false;
bool loraReady = false;

float lastRssi = 0;
float lastSnr = 0;

unsigned long lastOledMs = 0;
unsigned long lastSeg7Ms = 0;
unsigned long lastHeartbeatMs = 0;
unsigned long lastInputMs = 0;
unsigned long lastLoraPollMs = 0;

long lastBeepSecond = -1;

String oledOverlay = "";
unsigned long oledOverlayUntil = 0;

// Non-blocking beep sequencer
BeepPattern activeBeepPattern = BEEP_NONE;
uint8_t beepStep = 0;
bool beepOutputOn = false;
unsigned long beepNextMs = 0;

// Remote command tracking
uint32_t outgoingCounter = 0;

// =============================================================================
// FORWARD DECLARATIONS
// =============================================================================

void setDefaultConfig();
void loadConfig();
void saveConfig();
void applyProfile(GameProfile p);
void clampConfig();

void setupPins();
void setupDisplays();
void setupAudio();
void setupWiFi();
void setupWebServer();
void setupLoRa();

void loopInputs();
void loopDummy();
void loopCountdown();
void loopPhase();
void loopLockout();
void loopBuzzer();
void loopLoRa();
void loopHeartbeat();
void loopWeb();

void transitionTo(DeviceState newState);
void startMissionTimer();
void resetRuntime(bool keepConfig);

void handleArmLogic();
void handleDisarmLogic();
void handleKeypadForArm(char key);
void handleKeypadForDisarm(char key);
void wrongCode();

bool armSwitchOn();
bool redButtonPressed();
bool dummyRaw();
bool prereqArmOk();
bool prereqDisarmOk();
bool redHeldEnough();
bool switchAndButtonActive();

void updateOled();
void updateSeg7();
void showOverlay(const String &msg, unsigned long ms);

void playMp3(uint8_t track);
void startBeepPattern(BeepPattern pattern);
void buzzerWrite(bool on);

String formatTime(long ms);
String stateLabel();
String phaseLabel();
String themeLabel();
String profileLabel();
String armMethodLabel();
String disarmMethodLabel();
String penaltyLabel();

String htmlEscape(String s);
String buildWebPage();

void handleRoot();
void handleSave();
void handleActionArm();
void handleActionDisarm();
void handleActionReset();
void handleActionDisable();
void handleStatusJson();

void sendLoRaFrame(const String &to, const String &cmd, const String &value);
void sendLoRaStatus();
void handleLoRaFrame(const String &frame);
String makeMessageId();
String getFramePart(const String &s, int index);
bool constantTimeEquals(const String &a, const String &b);

int batteryPercent();

// =============================================================================
// CONFIG
// =============================================================================

void setDefaultConfig() {
  cfg.profile = PROFILE_CUSTOM;
  cfg.theme = THEME_PAYLOAD;

  cfg.armMethod = ARM_ENTER_CODE;
  cfg.disarmMethod = DISARM_ENTER_CODE;
  cfg.wrongPenalty = PENALTY_TEMP_LOCKOUT;

  strlcpy(cfg.armCode, "1919", sizeof(cfg.armCode));
  strlcpy(cfg.disarmCode, "0420", sizeof(cfg.disarmCode));
  strlcpy(cfg.adminPin, "1983", sizeof(cfg.adminPin));

  cfg.timerSeconds = 300;
  cfg.holdRedMs = 3000;

  cfg.requireDummyToArm = false;
  cfg.requireDummyToDisarm = false;
  cfg.alertIfDummyRemovedActive = true;

  cfg.lockoutOnWrongCode = true;
  cfg.maxWrongAttempts = 3;
  cfg.lockoutDurationSecs = 45;
  cfg.wrongCodeTimePenaltySecs = 30;

  cfg.phase2Percent = 50;
  cfg.phase3Percent = 20;

  cfg.enableAudio = true;
  cfg.mp3Volume = 22;

  cfg.enableLoRa = true;
  cfg.requireLoraKey = true;
}

void loadConfig() {
  setDefaultConfig();

  prefs.begin("cerberus", true);

  cfg.profile = (GameProfile)prefs.getUInt("profile", cfg.profile);
  cfg.theme = (ObjectiveTheme)prefs.getUInt("theme", cfg.theme);

  cfg.armMethod = (ArmMethod)prefs.getUInt("armM", cfg.armMethod);
  cfg.disarmMethod = (DisarmMethod)prefs.getUInt("disM", cfg.disarmMethod);
  cfg.wrongPenalty = (WrongCodePenalty)prefs.getUInt("penalty", cfg.wrongPenalty);

  String arm = prefs.getString("armCode", cfg.armCode);
  String dis = prefs.getString("disCode", cfg.disarmCode);
  String pin = prefs.getString("adminPin", cfg.adminPin);

  arm.toCharArray(cfg.armCode, sizeof(cfg.armCode));
  dis.toCharArray(cfg.disarmCode, sizeof(cfg.disarmCode));
  pin.toCharArray(cfg.adminPin, sizeof(cfg.adminPin));

  cfg.timerSeconds = prefs.getULong("timer", cfg.timerSeconds);
  cfg.holdRedMs = prefs.getULong("holdMs", cfg.holdRedMs);

  cfg.requireDummyToArm = prefs.getBool("dumArm", cfg.requireDummyToArm);
  cfg.requireDummyToDisarm = prefs.getBool("dumDis", cfg.requireDummyToDisarm);
  cfg.alertIfDummyRemovedActive = prefs.getBool("dumAlert", cfg.alertIfDummyRemovedActive);

  cfg.lockoutOnWrongCode = prefs.getBool("lockout", cfg.lockoutOnWrongCode);
  cfg.maxWrongAttempts = prefs.getInt("maxWrong", cfg.maxWrongAttempts);
  cfg.lockoutDurationSecs = prefs.getInt("lockSecs", cfg.lockoutDurationSecs);
  cfg.wrongCodeTimePenaltySecs = prefs.getInt("penSecs", cfg.wrongCodeTimePenaltySecs);

  cfg.phase2Percent = prefs.getUInt("ph2", cfg.phase2Percent);
  cfg.phase3Percent = prefs.getUInt("ph3", cfg.phase3Percent);

  cfg.enableAudio = prefs.getBool("audio", cfg.enableAudio);
  cfg.mp3Volume = prefs.getInt("vol", cfg.mp3Volume);

  cfg.enableLoRa = prefs.getBool("lora", cfg.enableLoRa);
  cfg.requireLoraKey = prefs.getBool("loraKey", cfg.requireLoraKey);

  prefs.end();

  if (strlen(cfg.armCode) == 0) strlcpy(cfg.armCode, "1919", sizeof(cfg.armCode));
  if (strlen(cfg.disarmCode) == 0) strlcpy(cfg.disarmCode, "0420", sizeof(cfg.disarmCode));
  if (strlen(cfg.adminPin) == 0) strlcpy(cfg.adminPin, "1983", sizeof(cfg.adminPin));

  clampConfig();
}

void saveConfig() {
  clampConfig();

  prefs.begin("cerberus", false);

  prefs.putUInt("profile", cfg.profile);
  prefs.putUInt("theme", cfg.theme);

  prefs.putUInt("armM", cfg.armMethod);
  prefs.putUInt("disM", cfg.disarmMethod);
  prefs.putUInt("penalty", cfg.wrongPenalty);

  prefs.putString("armCode", cfg.armCode);
  prefs.putString("disCode", cfg.disarmCode);
  prefs.putString("adminPin", cfg.adminPin);

  prefs.putULong("timer", cfg.timerSeconds);
  prefs.putULong("holdMs", cfg.holdRedMs);

  prefs.putBool("dumArm", cfg.requireDummyToArm);
  prefs.putBool("dumDis", cfg.requireDummyToDisarm);
  prefs.putBool("dumAlert", cfg.alertIfDummyRemovedActive);

  prefs.putBool("lockout", cfg.lockoutOnWrongCode);
  prefs.putInt("maxWrong", cfg.maxWrongAttempts);
  prefs.putInt("lockSecs", cfg.lockoutDurationSecs);
  prefs.putInt("penSecs", cfg.wrongCodeTimePenaltySecs);

  prefs.putUInt("ph2", cfg.phase2Percent);
  prefs.putUInt("ph3", cfg.phase3Percent);

  prefs.putBool("audio", cfg.enableAudio);
  prefs.putInt("vol", cfg.mp3Volume);

  prefs.putBool("lora", cfg.enableLoRa);
  prefs.putBool("loraKey", cfg.requireLoraKey);

  prefs.end();
}

void clampConfig() {
  if (cfg.profile > PROFILE_PAYLOAD_LINK) cfg.profile = PROFILE_CUSTOM;
  if (cfg.theme > THEME_DATA_TERMINAL) cfg.theme = THEME_PAYLOAD;

  if (cfg.armMethod > ARM_DUMMY_AND_CODE) cfg.armMethod = ARM_ENTER_CODE;
  if (cfg.disarmMethod > DISARM_MULTI_STAGE) cfg.disarmMethod = DISARM_ENTER_CODE;
  if (cfg.wrongPenalty > PENALTY_FORCE_PHASE_3) cfg.wrongPenalty = PENALTY_TEMP_LOCKOUT;

  cfg.timerSeconds = constrain(cfg.timerSeconds, 10UL, 7200UL);
  cfg.holdRedMs = constrain(cfg.holdRedMs, 500UL, 10000UL);

  cfg.maxWrongAttempts = constrain(cfg.maxWrongAttempts, 1, 10);
  cfg.lockoutDurationSecs = constrain(cfg.lockoutDurationSecs, 5, 3600);
  cfg.wrongCodeTimePenaltySecs = constrain(cfg.wrongCodeTimePenaltySecs, 5, 600);

  cfg.phase2Percent = constrain(cfg.phase2Percent, (uint8_t)10, (uint8_t)90);
  cfg.phase3Percent = constrain(cfg.phase3Percent, (uint8_t)5, (uint8_t)80);

  if (cfg.phase3Percent >= cfg.phase2Percent) {
    cfg.phase3Percent = cfg.phase2Percent / 2;
    if (cfg.phase3Percent < 5) cfg.phase3Percent = 5;
  }

  cfg.mp3Volume = constrain(cfg.mp3Volume, 0, 30);
}

void applyProfile(GameProfile p) {
  cfg.profile = p;

  switch (p) {
    case PROFILE_SEARCH_DESTROY:
      cfg.theme = THEME_PAYLOAD;
      cfg.armMethod = ARM_ENTER_CODE;
      cfg.disarmMethod = DISARM_ENTER_CODE;
      cfg.timerSeconds = 300;
      cfg.requireDummyToArm = false;
      cfg.requireDummyToDisarm = false;
      cfg.wrongPenalty = PENALTY_SUBTRACT_TIME;
      cfg.phase2Percent = 50;
      cfg.phase3Percent = 20;
      break;

    case PROFILE_MISSILE_GUIDANCE:
      cfg.theme = THEME_GUIDANCE;
      cfg.armMethod = ARM_SWITCH_AND_BUTTON;
      cfg.disarmMethod = DISARM_MULTI_STAGE;
      cfg.timerSeconds = 600;
      cfg.requireDummyToArm = true;
      cfg.requireDummyToDisarm = true;
      cfg.wrongPenalty = PENALTY_FORCE_PHASE_2;
      cfg.phase2Percent = 40;
      cfg.phase3Percent = 15;
      break;

    case PROFILE_REACTOR_CORE:
      cfg.theme = THEME_REACTOR;
      cfg.armMethod = ARM_DUMMY_AND_CODE;
      cfg.disarmMethod = DISARM_MULTI_STAGE;
      cfg.timerSeconds = 900;
      cfg.requireDummyToArm = true;
      cfg.requireDummyToDisarm = true;
      cfg.wrongPenalty = PENALTY_TEMP_LOCKOUT;
      cfg.phase2Percent = 60;
      cfg.phase3Percent = 25;
      break;

    case PROFILE_DEADMAN_SWITCH:
      cfg.theme = THEME_CONTROLLER;
      cfg.armMethod = ARM_HOLD_RED;
      cfg.disarmMethod = DISARM_HOLD_RED;
      cfg.timerSeconds = 180;
      cfg.requireDummyToArm = false;
      cfg.requireDummyToDisarm = false;
      cfg.wrongPenalty = PENALTY_BEEP_ONLY;
      cfg.phase2Percent = 50;
      cfg.phase3Percent = 20;
      break;

    case PROFILE_PAYLOAD_LINK:
      cfg.theme = THEME_DATA_TERMINAL;
      cfg.armMethod = ARM_DUMMY_AND_CODE;
      cfg.disarmMethod = DISARM_REMOVE_DUMMY;
      cfg.timerSeconds = 420;
      cfg.requireDummyToArm = true;
      cfg.requireDummyToDisarm = false;
      cfg.wrongPenalty = PENALTY_FORCE_PHASE_3;
      cfg.phase2Percent = 50;
      cfg.phase3Percent = 20;
      break;

    case PROFILE_CUSTOM:
    default:
      break;
  }

  clampConfig();
}

// =============================================================================
// LABELS
// =============================================================================

String profileLabel() {
  switch (cfg.profile) {
    case PROFILE_CUSTOM: return "CUSTOM";
    case PROFILE_SEARCH_DESTROY: return "SEARCH/DESTROY";
    case PROFILE_MISSILE_GUIDANCE: return "MISSILE GUIDANCE";
    case PROFILE_REACTOR_CORE: return "REACTOR CORE";
    case PROFILE_DEADMAN_SWITCH: return "DEADMAN SWITCH";
    case PROFILE_PAYLOAD_LINK: return "PAYLOAD LINK";
  }
  return "UNKNOWN";
}

String themeLabel() {
  switch (cfg.theme) {
    case THEME_PAYLOAD: return "PAYLOAD DEVICE";
    case THEME_GUIDANCE: return "GUIDANCE SYSTEM";
    case THEME_CONTROLLER: return "CONTROL UNIT";
    case THEME_REACTOR: return "REACTOR CORE";
    case THEME_DATA_TERMINAL: return "DATA TERMINAL";
  }
  return "UNKNOWN";
}

String stateLabel() {
  switch (deviceState) {
    case STATE_BOOTING: return "BOOTING";
    case STATE_IDLE: return "IDLE";
    case STATE_WAIT_PREREQ: return "CONNECT MODULE";
    case STATE_STANDBY: return "STANDBY";
    case STATE_ARMING: return "ARMING";
    case STATE_ACTIVE: return "ACTIVE";
    case STATE_DISARMING: return "DISARMING";
    case STATE_DISARMED: return "COMPLETE";
    case STATE_MISSION_FAILED: return "MISSION FAIL";
    case STATE_LOCKED_OUT: return "LOCKED";
    case STATE_ADMIN_DISABLED: return "DISABLED";
  }
  return "UNKNOWN";
}

String phaseLabel() {
  switch (devicePhase) {
    case PHASE_SAFE: return "SAFE";
    case PHASE_1: return "PHASE 1";
    case PHASE_2: return "WARNING";
    case PHASE_3: return "CRITICAL";
  }
  return "";
}

String armMethodLabel() {
  switch (cfg.armMethod) {
    case ARM_HOLD_RED: return "Hold RED";
    case ARM_ENTER_CODE: return "Enter code";
    case ARM_SWITCH_AND_BUTTON: return "Switch + RED";
    case ARM_DUMMY_AND_CODE: return "Module + code";
  }
  return "Unknown";
}

String disarmMethodLabel() {
  switch (cfg.disarmMethod) {
    case DISARM_HOLD_RED: return "Hold RED";
    case DISARM_ENTER_CODE: return "Enter code";
    case DISARM_SWITCH_AND_BUTTON: return "Safe + RED";
    case DISARM_REMOVE_DUMMY: return "Remove module";
    case DISARM_MULTI_STAGE: return "Multi-stage";
  }
  return "Unknown";
}

String penaltyLabel() {
  switch (cfg.wrongPenalty) {
    case PENALTY_BEEP_ONLY: return "Beep only";
    case PENALTY_SUBTRACT_TIME: return "Subtract time";
    case PENALTY_TEMP_LOCKOUT: return "Temp lockout";
    case PENALTY_FORCE_PHASE_2: return "Force phase 2";
    case PENALTY_FORCE_PHASE_3: return "Force phase 3";
  }
  return "Unknown";
}

String formatTime(long ms) {
  if (ms < 0) ms = 0;
  int totalSec = (int)(ms / 1000);
  int minutes = totalSec / 60;
  int seconds = totalSec % 60;

  char buf[8];
  snprintf(buf, sizeof(buf), "%02d:%02d", minutes, seconds);
  return String(buf);
}

// =============================================================================
// INPUTS
// =============================================================================

bool armSwitchOn() {
  return digitalRead(PIN_ARM_SWITCH) == LOW;
}

bool redButtonPressed() {
  return digitalRead(PIN_RED_BUTTON) == LOW;
}

bool dummyRaw() {
  return digitalRead(PIN_DUMMY_PROP) == LOW;
}

bool prereqArmOk() {
  if (cfg.requireDummyToArm && !dummyConnected) return false;
  return true;
}

bool prereqDisarmOk() {
  if (cfg.requireDummyToDisarm && !dummyConnected) return false;
  return true;
}

bool redHeldEnough() {
  return redButtonPressed() && (millis() - actionStartMs >= cfg.holdRedMs);
}

bool switchAndButtonActive() {
  return armSwitchOn() && redButtonPressed();
}

// =============================================================================
// BUZZER
// =============================================================================

void buzzerWrite(bool on) {
  digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
  beepOutputOn = on;
}

void startBeepPattern(BeepPattern pattern) {
  activeBeepPattern = pattern;
  beepStep = 0;
  beepNextMs = 0;
  buzzerWrite(false);
}

void loopBuzzer() {
  unsigned long now = millis();

  if (activeBeepPattern == BEEP_NONE) return;
  if (now < beepNextMs) return;

  uint16_t onMs = 0;
  uint16_t offMs = 0;
  uint8_t maxSteps = 0;

  switch (activeBeepPattern) {
    case BEEP_BOOT:
      onMs = 60; offMs = 80; maxSteps = 4;
      break;
    case BEEP_CLICK:
      onMs = 25; offMs = 10; maxSteps = 2;
      break;
    case BEEP_ARMED:
      onMs = 80; offMs = 80; maxSteps = 6;
      break;
    case BEEP_ERROR:
      onMs = 300; offMs = 100; maxSteps = 2;
      break;
    case BEEP_SUCCESS:
      onMs = 80; offMs = 70; maxSteps = 10;
      break;
    case BEEP_WARNING:
      onMs = 150; offMs = 100; maxSteps = 6;
      break;
    case BEEP_FAIL:
      onMs = 60; offMs = 40; maxSteps = 16;
      break;
    default:
      activeBeepPattern = BEEP_NONE;
      buzzerWrite(false);
      return;
  }

  if (beepStep >= maxSteps) {
    activeBeepPattern = BEEP_NONE;
    buzzerWrite(false);
    return;
  }

  if (beepStep % 2 == 0) {
    buzzerWrite(true);
    beepNextMs = now + onMs;
  } else {
    buzzerWrite(false);
    beepNextMs = now + offMs;
  }

  beepStep++;
}

// =============================================================================
// MP3
// =============================================================================

void playMp3(uint8_t track) {
  if (!cfg.enableAudio) return;
  if (!mp3Ready) return;

  mp3Player.volume(cfg.mp3Volume);
  mp3Player.play(track);
}

// =============================================================================
// DISPLAY
// =============================================================================

#define SEG_DASH   0x40
#define SEG_d      0x5E
#define SEG_E      0x79
#define SEG_F      0x71
#define SEG_A      0x77
#define SEG_r      0x50
#define SEG_L      0x38
#define SEG_O      0x3F
#define SEG_C      0x39

void updateSeg7() {
  if (millis() - lastSeg7Ms < SEG7_REFRESH_MS) return;
  lastSeg7Ms = millis();

  seg7.clear();

  if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
    long ms = timerRemainMs;
    if (ms < 0) ms = 0;

    int totalSec = (int)(ms / 1000);
    int minutes = totalSec / 60;
    int seconds = totalSec % 60;

    if (minutes > 99) {
      minutes = 99;
      seconds = 59;
    }

    bool colonOn = true;
    if (devicePhase == PHASE_2) colonOn = ((millis() / 500) % 2 == 0);
    if (devicePhase == PHASE_3) colonOn = ((millis() / 200) % 2 == 0);

    seg7.writeDigitNum(0, minutes / 10, false);
    seg7.writeDigitNum(1, minutes % 10, false);
    seg7.drawColon(colonOn);
    seg7.writeDigitNum(3, seconds / 10, false);
    seg7.writeDigitNum(4, seconds % 10, false);
  }

  else if (deviceState == STATE_DISARMED) {
    seg7.writeDigitRaw(0, SEG_d);
    seg7.writeDigitRaw(1, SEG_O);
    seg7.drawColon(false);
    seg7.writeDigitRaw(3, SEG_n);
    seg7.writeDigitRaw(4, SEG_E);
  }

  else if (deviceState == STATE_MISSION_FAILED) {
    if ((millis() / 250) % 2 == 0) {
      seg7.writeDigitNum(0, 0);
      seg7.writeDigitNum(1, 0);
      seg7.drawColon(true);
      seg7.writeDigitNum(3, 0);
      seg7.writeDigitNum(4, 0);
    }
  }

  else if (deviceState == STATE_LOCKED_OUT) {
    long remain = ((long)lockoutEndMs - (long)millis()) / 1000;
    if (remain < 0) remain = 0;

    int minutes = remain / 60;
    int seconds = remain % 60;

    seg7.writeDigitNum(0, minutes / 10, false);
    seg7.writeDigitNum(1, minutes % 10, false);
    seg7.drawColon(true);
    seg7.writeDigitNum(3, seconds / 10, false);
    seg7.writeDigitNum(4, seconds % 10, false);
  }

  else if (deviceState == STATE_ARMING) {
    if ((millis() / 350) % 2 == 0) {
      seg7.writeDigitRaw(0, SEG_A);
      seg7.writeDigitRaw(1, SEG_r);
      seg7.drawColon(false);
      seg7.writeDigitRaw(3, SEG_DASH);
      seg7.writeDigitRaw(4, SEG_DASH);
    }
  }

  else {
    seg7.writeDigitRaw(0, SEG_DASH);
    seg7.writeDigitRaw(1, SEG_DASH);
    seg7.drawColon(false);
    seg7.writeDigitRaw(3, SEG_DASH);
    seg7.writeDigitRaw(4, SEG_DASH);
  }

  seg7.writeDisplay();
}

void updateOled() {
  if (millis() - lastOledMs < OLED_REFRESH_MS) return;
  lastOledMs = millis();

  oled.clearBuffer();

  oled.setDrawColor(1);
  oled.drawBox(0, 0, 128, 13);
  oled.setDrawColor(0);
  oled.setFont(u8g2_font_7x13B_tf);

  String title = themeLabel();
  int titleW = oled.getStrWidth(title.c_str());
  oled.drawStr((128 - titleW) / 2, 11, title.c_str());

  oled.setDrawColor(1);
  oled.setFont(u8g2_font_6x10_tf);

  oled.drawStr(0, 24, stateLabel().c_str());

  if (devicePhase != PHASE_SAFE) {
    String ph = phaseLabel();
    int phW = oled.getStrWidth(ph.c_str());
    oled.drawStr(128 - phW, 24, ph.c_str());
  }

  oled.drawHLine(0, 27, 128);

  switch (deviceState) {
    case STATE_IDLE:
      oled.drawStr(0, 40, "Awaiting orders.");
      oled.drawStr(0, 52, "WiFi: " AP_SSID);
      oled.drawStr(0, 63, "Open 192.168.4.1");
      break;

    case STATE_WAIT_PREREQ:
      oled.drawStr(0, 40, "CONNECT MODULE");
      if (dummyConnected) {
        oled.drawStr(0, 53, "[ LINK OK ]");
      } else if ((millis() / 500) % 2 == 0) {
        oled.drawStr(0, 53, "[ WAITING ]");
      }
      break;

    case STATE_STANDBY:
      oled.drawStr(0, 39, "READY");
      oled.drawStr(0, 51, ("ARM: " + armMethodLabel()).c_str());
      oled.drawStr(0, 63, ("TIME: " + formatTime((long)cfg.timerSeconds * 1000)).c_str());
      break;

    case STATE_ARMING:
      if (cfg.armMethod == ARM_HOLD_RED) {
        oled.drawStr(0, 39, "HOLD RED TO ARM");
        int fill = (int)((millis() - actionStartMs) * 126 / cfg.holdRedMs);
        fill = constrain(fill, 0, 126);
        oled.drawFrame(1, 44, 126, 10);
        oled.drawBox(1, 44, fill, 10);
      } else {
        oled.drawStr(0, 39, "ARM SEQUENCE");
        String masked = "";
        for (unsigned int i = 0; i < codeInput.length(); i++) masked += "*";
        oled.setFont(u8g2_font_10x20_tf);
        int mw = oled.getStrWidth(masked.c_str());
        oled.drawStr((128 - mw) / 2, 62, masked.c_str());
        oled.setFont(u8g2_font_6x10_tf);
      }
      break;

    case STATE_ACTIVE:
      oled.setFont(u8g2_font_10x20_tf);
      {
        String timeStr = formatTime(timerRemainMs);
        int tw = oled.getStrWidth(timeStr.c_str());
        oled.drawStr((128 - tw) / 2, 52, timeStr.c_str());
      }
      oled.setFont(u8g2_font_6x10_tf);
      oled.drawStr(0, 63, ("DISARM: " + disarmMethodLabel()).c_str());
      break;

    case STATE_DISARMING:
      oled.drawStr(0, 38, "DISARMING");
      if (cfg.disarmMethod == DISARM_HOLD_RED || cfg.disarmMethod == DISARM_SWITCH_AND_BUTTON) {
        int fill = (int)((millis() - actionStartMs) * 126 / cfg.holdRedMs);
        fill = constrain(fill, 0, 126);
        oled.drawFrame(1, 43, 126, 10);
        oled.drawBox(1, 43, fill, 10);
        oled.drawStr(72, 63, formatTime(timerRemainMs).c_str());
      } else if (cfg.disarmMethod == DISARM_MULTI_STAGE) {
        oled.drawStr(0, 50, "1 Module  2 Safe");
        oled.drawStr(0, 62, "3 Code    4 RED");
      } else {
        String masked = "";
        for (unsigned int i = 0; i < codeInput.length(); i++) masked += "*";
        oled.setFont(u8g2_font_10x20_tf);
        int mw = oled.getStrWidth(masked.c_str());
        oled.drawStr((128 - mw) / 2, 62, masked.c_str());
        oled.setFont(u8g2_font_6x10_tf);
      }
      break;

    case STATE_DISARMED:
      oled.setFont(u8g2_font_10x20_tf);
      {
        String msg = "COMPLETE";
        int mw = oled.getStrWidth(msg.c_str());
        oled.drawStr((128 - mw) / 2, 52, msg.c_str());
      }
      oled.setFont(u8g2_font_6x10_tf);
      break;

    case STATE_MISSION_FAILED:
      oled.setFont(u8g2_font_10x20_tf);
      if ((millis() / 300) % 2 == 0) {
        String msg = "FAILED";
        int mw = oled.getStrWidth(msg.c_str());
        oled.drawStr((128 - mw) / 2, 52, msg.c_str());
      }
      oled.setFont(u8g2_font_6x10_tf);
      break;

    case STATE_LOCKED_OUT:
      oled.drawStr(0, 39, "ACCESS LOCKED");
      {
        long remain = ((long)lockoutEndMs - (long)millis()) / 1000;
        if (remain < 0) remain = 0;
        oled.drawStr(0, 52, ("WAIT: " + String(remain) + "s").c_str());
      }
      break;

    case STATE_ADMIN_DISABLED:
      oled.drawStr(0, 40, "ADMIN DISABLED");
      oled.drawStr(0, 53, "Use web or LoRa");
      break;

    default:
      break;
  }

  if (oledOverlayUntil > millis() && oledOverlay.length() > 0) {
    int w = oled.getStrWidth(oledOverlay.c_str()) + 10;
    if (w > 126) w = 126;
    int x = (128 - w) / 2;

    oled.setDrawColor(0);
    oled.drawBox(x - 2, 29, w + 4, 14);
    oled.setDrawColor(1);
    oled.drawRFrame(x - 2, 29, w + 4, 14, 2);
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(x + 3, 40, oledOverlay.c_str());
  }

  oled.setFont(u8g2_font_5x8_tf);
  oled.drawStr(0, 8, DEVICE_ID);

  if (loraReady) {
    int pct = map((int)lastRssi, -120, -40, 0, 100);
    pct = constrain(pct, 0, 100);
    for (int i = 0; i < 3; i++) {
      int h = 3 + i * 2;
      int x = 116 + i * 4;
      int y = 11 - h;
      if (pct > i * 33) oled.drawBox(x, y, 3, h);
      else oled.drawFrame(x, y, 3, h);
    }
  }

  oled.sendBuffer();
}

void showOverlay(const String &msg, unsigned long ms) {
  oledOverlay = msg;
  oledOverlayUntil = millis() + ms;
}

// =============================================================================
// STATE MACHINE
// =============================================================================

void transitionTo(DeviceState newState) {
  if (newState == deviceState) return;

  DeviceState oldState = deviceState;
  deviceState = newState;
  stateEnteredMs = millis();

  Serial.print("[STATE] ");
  Serial.println(stateLabel());

  switch (newState) {
    case STATE_IDLE:
      devicePhase = PHASE_SAFE;
      lastAnnouncedPhase = PHASE_SAFE;
      timerRemainMs = (long)cfg.timerSeconds * 1000;
      actionActive = false;
      codeInput = "";
      wrongAttempts = 0;
      lastBeepSecond = -1;
      showOverlay("IDLE", 1200);
      break;

    case STATE_WAIT_PREREQ:
      devicePhase = PHASE_SAFE;
      actionActive = false;
      codeInput = "";
      showOverlay("CONNECT MODULE", 1600);
      startBeepPattern(BEEP_WARNING);
      break;

    case STATE_STANDBY:
      devicePhase = PHASE_SAFE;
      actionActive = false;
      codeInput = "";
      timerRemainMs = (long)cfg.timerSeconds * 1000;
      showOverlay("STANDBY", 1200);
      break;

    case STATE_ARMING:
      actionStartMs = millis();
      actionActive = true;
      codeInput = "";
      playMp3(TRACK_ARMING_INIT);
      startBeepPattern(BEEP_CLICK);
      break;

    case STATE_ACTIVE:
      actionActive = false;
      codeInput = "";
      wrongAttempts = 0;

      if (oldState != STATE_DISARMING) {
        startMissionTimer();
        startBeepPattern(BEEP_ARMED);

        switch (cfg.theme) {
          case THEME_PAYLOAD: playMp3(TRACK_ARMED_PAYLOAD); break;
          case THEME_GUIDANCE: playMp3(TRACK_ARMED_GUIDANCE); break;
          case THEME_CONTROLLER: playMp3(TRACK_ARMED_CONTROLLER); break;
          case THEME_REACTOR: playMp3(TRACK_ARMED_PAYLOAD); break;
          case THEME_DATA_TERMINAL: playMp3(TRACK_GUIDANCE_LOCK); break;
        }

        sendLoRaFrame("ALL", "ACTIVE", String(cfg.timerSeconds));
      }

      showOverlay("ACTIVE", 1200);
      break;

    case STATE_DISARMING:
      actionStartMs = millis();
      actionActive = true;
      codeInput = "";
      showOverlay("DISARMING", 1000);
      break;

    case STATE_DISARMED:
      devicePhase = PHASE_SAFE;
      actionActive = false;
      codeInput = "";
      playMp3(TRACK_DISARMED);
      startBeepPattern(BEEP_SUCCESS);
      sendLoRaFrame("ALL", "OBJECTIVE_COMPLETE", "OK");
      showOverlay("COMPLETE", 2500);
      break;

    case STATE_MISSION_FAILED:
      devicePhase = PHASE_SAFE;
      actionActive = false;
      codeInput = "";
      timerRemainMs = 0;
      playMp3(TRACK_MISSION_FAILED);
      startBeepPattern(BEEP_FAIL);
      sendLoRaFrame("ALL", "MISSION_FAILED", "TIMER_EXPIRED");
      showOverlay("MISSION FAILED", 3000);
      break;

    case STATE_LOCKED_OUT:
      actionActive = false;
      codeInput = "";
      lockoutEndMs = millis() + ((unsigned long)cfg.lockoutDurationSecs * 1000UL);
      playMp3(TRACK_LOCKOUT);
      startBeepPattern(BEEP_ERROR);
      sendLoRaFrame("ALL", "LOCKOUT", String(cfg.lockoutDurationSecs));
      showOverlay("LOCKED", 2000);
      break;

    case STATE_ADMIN_DISABLED:
      devicePhase = PHASE_SAFE;
      actionActive = false;
      codeInput = "";
      playMp3(TRACK_ADMIN_DISABLED);
      sendLoRaFrame("ALL", "ADMIN_DISABLED", "");
      showOverlay("DISABLED", 2000);
      break;

    default:
      break;
  }

  sendLoRaStatus();
}

void startMissionTimer() {
  devicePhase = PHASE_1;
  lastAnnouncedPhase = PHASE_1;
  timerRemainMs = (long)cfg.timerSeconds * 1000;
  timerEndMs = millis() + (unsigned long)timerRemainMs;
  lastBeepSecond = -1;
}

void resetRuntime(bool keepConfig) {
  (void)keepConfig;

  wrongAttempts = 0;
  codeInput = "";
  actionActive = false;
  devicePhase = PHASE_SAFE;
  lastAnnouncedPhase = PHASE_SAFE;
  timerRemainMs = (long)cfg.timerSeconds * 1000;

  if (cfg.requireDummyToArm && !dummyConnected) transitionTo(STATE_WAIT_PREREQ);
  else transitionTo(STATE_STANDBY);
}

// =============================================================================
// GAME LOGIC
// =============================================================================

void loopInputs() {
  if (millis() - lastInputMs < INPUT_TICK_MS) return;
  lastInputMs = millis();

  if (deviceState == STATE_ADMIN_DISABLED) return;
  if (deviceState == STATE_LOCKED_OUT) return;

  if (deviceState == STATE_STANDBY || deviceState == STATE_ARMING) {
    handleArmLogic();
  }

  if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
    handleDisarmLogic();
  }
}

void handleArmLogic() {
  if (!prereqArmOk()) {
    if (deviceState != STATE_WAIT_PREREQ) transitionTo(STATE_WAIT_PREREQ);
    return;
  }

  char key = keypad.getKey();

  switch (cfg.armMethod) {
    case ARM_HOLD_RED:
      if (redButtonPressed()) {
        if (deviceState == STATE_STANDBY) transitionTo(STATE_ARMING);
        if (redHeldEnough()) transitionTo(STATE_ACTIVE);
      } else {
        if (deviceState == STATE_ARMING) transitionTo(STATE_STANDBY);
      }
      break;

    case ARM_ENTER_CODE:
      if (key != NO_KEY) handleKeypadForArm(key);
      break;

    case ARM_SWITCH_AND_BUTTON:
      if (!armSwitchOn()) {
        if (deviceState == STATE_ARMING) transitionTo(STATE_STANDBY);
        break;
      }

      if (redButtonPressed()) {
        if (deviceState == STATE_STANDBY) transitionTo(STATE_ARMING);
        if (millis() - actionStartMs >= 600) transitionTo(STATE_ACTIVE);
      } else {
        if (deviceState == STATE_ARMING) transitionTo(STATE_STANDBY);
      }
      break;

    case ARM_DUMMY_AND_CODE:
      if (!dummyConnected) {
        transitionTo(STATE_WAIT_PREREQ);
      } else if (key != NO_KEY) {
        handleKeypadForArm(key);
      }
      break;
  }
}

void handleDisarmLogic() {
  if (!prereqDisarmOk()) {
    showOverlay("MODULE REQUIRED", 1000);
    return;
  }

  char key = keypad.getKey();

  switch (cfg.disarmMethod) {
    case DISARM_HOLD_RED:
      if (redButtonPressed()) {
        if (deviceState == STATE_ACTIVE) transitionTo(STATE_DISARMING);
        if (redHeldEnough()) transitionTo(STATE_DISARMED);
      } else {
        if (deviceState == STATE_DISARMING) transitionTo(STATE_ACTIVE);
      }
      break;

    case DISARM_ENTER_CODE:
      if (key != NO_KEY) handleKeypadForDisarm(key);
      break;

    case DISARM_SWITCH_AND_BUTTON:
      if (armSwitchOn()) {
        if (deviceState == STATE_DISARMING) transitionTo(STATE_ACTIVE);
        break;
      }

      if (redButtonPressed()) {
        if (deviceState == STATE_ACTIVE) transitionTo(STATE_DISARMING);
        if (millis() - actionStartMs >= 600) transitionTo(STATE_DISARMED);
      } else {
        if (deviceState == STATE_DISARMING) transitionTo(STATE_ACTIVE);
      }
      break;

    case DISARM_REMOVE_DUMMY:
      if (!dummyConnected) transitionTo(STATE_DISARMED);
      break;

    case DISARM_MULTI_STAGE:
      if (deviceState == STATE_ACTIVE) transitionTo(STATE_DISARMING);

      if (!dummyConnected) {
        showOverlay("STAGE 1: MODULE", 1000);
        break;
      }

      if (armSwitchOn()) {
        showOverlay("STAGE 2: SAFE", 1000);
        break;
      }

      if (key != NO_KEY) {
        if (key == '#') {
          if (constantTimeEquals(codeInput, String(cfg.disarmCode))) {
            codeInput = "";
            showOverlay("STAGE 4: HOLD RED", 1500);
          } else {
            wrongCode();
            codeInput = "";
          }
        } else if (key == '*') {
          codeInput = "";
          showOverlay("CLEARED", 800);
        } else if (codeInput.length() < 15) {
          codeInput += key;
          startBeepPattern(BEEP_CLICK);
        }
      }

      if (constantTimeEquals(codeInput, String(cfg.disarmCode))) {
        // Not normally reached because # clears input, but left as safe fallback.
        codeInput = "";
      }

      if (redButtonPressed() && codeInput.length() == 0) {
        if (!actionActive) {
          actionStartMs = millis();
          actionActive = true;
        }
        if (millis() - actionStartMs >= cfg.holdRedMs) {
          transitionTo(STATE_DISARMED);
        }
      } else {
        actionActive = false;
      }
      break;
  }
}

void handleKeypadForArm(char key) {
  if (deviceState == STATE_STANDBY) transitionTo(STATE_ARMING);

  if (key == '#') {
    if (constantTimeEquals(codeInput, String(cfg.armCode))) {
      codeInput = "";
      transitionTo(STATE_ACTIVE);
    } else {
      wrongCode();
      codeInput = "";
      if (deviceState == STATE_ARMING) transitionTo(STATE_STANDBY);
    }
  } else if (key == '*') {
    codeInput = "";
    if (deviceState == STATE_ARMING) transitionTo(STATE_STANDBY);
    showOverlay("CLEARED", 800);
  } else {
    if (codeInput.length() < 15) {
      codeInput += key;
      startBeepPattern(BEEP_CLICK);
    }
  }
}

void handleKeypadForDisarm(char key) {
  if (deviceState == STATE_ACTIVE) transitionTo(STATE_DISARMING);

  if (key == '#') {
    if (constantTimeEquals(codeInput, String(cfg.disarmCode))) {
      codeInput = "";
      transitionTo(STATE_DISARMED);
    } else {
      wrongCode();
      codeInput = "";
      if (deviceState == STATE_DISARMING) transitionTo(STATE_ACTIVE);
    }
  } else if (key == '*') {
    codeInput = "";
    if (deviceState == STATE_DISARMING) transitionTo(STATE_ACTIVE);
    showOverlay("CLEARED", 800);
  } else {
    if (codeInput.length() < 15) {
      codeInput += key;
      startBeepPattern(BEEP_CLICK);
    }
  }
}

void wrongCode() {
  wrongAttempts++;
  playMp3(TRACK_WRONG_CODE);
  startBeepPattern(BEEP_ERROR);
  showOverlay("WRONG CODE", 1500);
  sendLoRaFrame("ALL", "WRONG_CODE", String(wrongAttempts));

  if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
    switch (cfg.wrongPenalty) {
      case PENALTY_BEEP_ONLY:
        break;

      case PENALTY_SUBTRACT_TIME:
        timerEndMs -= ((unsigned long)cfg.wrongCodeTimePenaltySecs * 1000UL);
        showOverlay("-" + String(cfg.wrongCodeTimePenaltySecs) + " SEC", 1500);
        break;

      case PENALTY_TEMP_LOCKOUT:
        if (cfg.lockoutOnWrongCode && wrongAttempts >= cfg.maxWrongAttempts) {
          wrongAttempts = 0;
          lockoutEndMs = millis() + ((unsigned long)cfg.lockoutDurationSecs * 1000UL);
          showOverlay("KEYPAD LOCKED", 2000);
        }
        break;

      case PENALTY_FORCE_PHASE_2:
        if (devicePhase < PHASE_2) {
          devicePhase = PHASE_2;
          playMp3(TRACK_PHASE2);
        }
        break;

      case PENALTY_FORCE_PHASE_3:
        if (devicePhase < PHASE_3) {
          devicePhase = PHASE_3;
          playMp3(TRACK_PHASE3);
        }
        break;
    }
  } else {
    if (cfg.lockoutOnWrongCode && wrongAttempts >= cfg.maxWrongAttempts) {
      transitionTo(STATE_LOCKED_OUT);
    }
  }
}

// =============================================================================
// DUMMY PROP
// =============================================================================

void loopDummy() {
  bool raw = dummyRaw();

  if (raw != dummyLastRaw) {
    dummyLastRaw = raw;
    dummyChangedMs = millis();
  }

  if ((millis() - dummyChangedMs) >= DUMMY_DEBOUNCE_MS && raw != dummyStable) {
    dummyStable = raw;
    dummyConnected = dummyStable;

    if (dummyConnected) {
      playMp3(TRACK_PREREQ_MET);
      showOverlay("MODULE LINKED", 1500);
      sendLoRaFrame("ALL", "MODULE_LINKED", "");

      if (deviceState == STATE_WAIT_PREREQ) {
        transitionTo(STATE_STANDBY);
      }
    } else {
      showOverlay("MODULE REMOVED", 1500);
      sendLoRaFrame("ALL", "MODULE_REMOVED", "");

      if (deviceState == STATE_STANDBY && cfg.requireDummyToArm) {
        transitionTo(STATE_WAIT_PREREQ);
      }

      if ((deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) && cfg.alertIfDummyRemovedActive) {
        startBeepPattern(BEEP_WARNING);
      }
    }
  }
}

// =============================================================================
// COUNTDOWN / PHASE
// =============================================================================

void loopCountdown() {
  if (deviceState != STATE_ACTIVE && deviceState != STATE_DISARMING) return;

  timerRemainMs = (long)timerEndMs - (long)millis();

  if (timerRemainMs <= 0) {
    timerRemainMs = 0;
    transitionTo(STATE_MISSION_FAILED);
    return;
  }

  long remainSec = timerRemainMs / 1000;

  if (remainSec != lastBeepSecond) {
    lastBeepSecond = remainSec;

    if (remainSec <= 10 && remainSec > 0) {
      startBeepPattern(BEEP_WARNING);
    } else if (devicePhase == PHASE_3 && remainSec % 2 == 0) {
      startBeepPattern(BEEP_CLICK);
    } else if (devicePhase == PHASE_2 && remainSec % 5 == 0) {
      startBeepPattern(BEEP_CLICK);
    } else if (devicePhase == PHASE_1 && remainSec % 10 == 0) {
      startBeepPattern(BEEP_CLICK);
    }
  }
}

void loopPhase() {
  if (deviceState != STATE_ACTIVE && deviceState != STATE_DISARMING) return;
  if (timerRemainMs <= 0) return;

  long totalMs = (long)cfg.timerSeconds * 1000;
  int remainPct = (int)(timerRemainMs * 100L / totalMs);

  DevicePhase target = PHASE_1;

  if (remainPct <= cfg.phase3Percent) target = PHASE_3;
  else if (remainPct <= cfg.phase2Percent) target = PHASE_2;

  if (target != devicePhase) {
    devicePhase = target;

    if (devicePhase == PHASE_2 && lastAnnouncedPhase != PHASE_2) {
      lastAnnouncedPhase = PHASE_2;
      playMp3(TRACK_PHASE2);
      showOverlay("PHASE 2 WARNING", 2500);
      sendLoRaFrame("ALL", "PHASE", "2");
    }

    if (devicePhase == PHASE_3 && lastAnnouncedPhase != PHASE_3) {
      lastAnnouncedPhase = PHASE_3;
      playMp3(TRACK_PHASE3);
      showOverlay("PHASE 3 CRITICAL", 2500);
      sendLoRaFrame("ALL", "PHASE", "3");
    }
  }
}

void loopLockout() {
  if (deviceState != STATE_LOCKED_OUT) return;

  if (millis() >= lockoutEndMs) {
    wrongAttempts = 0;
    codeInput = "";
    transitionTo(STATE_STANDBY);
    showOverlay("LOCKOUT CLEAR", 1500);
  }
}

// =============================================================================
// LORA
// =============================================================================

String makeMessageId() {
  outgoingCounter++;
  return String(DEVICE_ID) + "-" + String(outgoingCounter);
}

void sendLoRaFrame(const String &to, const String &cmd, const String &value) {
  if (!cfg.enableLoRa) return;
  if (!loraReady) return;

  String frame = "";
  frame += LORA_SHARED_KEY;
  frame += "|";
  frame += to;
  frame += "|";
  frame += DEVICE_ID;
  frame += "|";
  frame += cmd;
  frame += "|";
  frame += value;
  frame += "|";
  frame += makeMessageId();

  radio.transmit(frame);
}

void sendLoRaStatus() {
  String value = "";
  value += "state=" + stateLabel();
  value += ";theme=" + themeLabel();
  value += ";profile=" + profileLabel();
  value += ";phase=" + String((int)devicePhase);
  value += ";time=" + formatTime(timerRemainMs);
  value += ";dummy=" + String(dummyConnected ? "1" : "0");
  value += ";battery=" + String(batteryPercent());
  value += ";rssi=" + String(lastRssi);

  sendLoRaFrame("ALL", "STATUS", value);
}

void loopLoRa() {
  if (!cfg.enableLoRa) return;
  if (!loraReady) return;
  if (millis() - lastLoraPollMs < LORA_POLL_MS) return;
  lastLoraPollMs = millis();

  String rx;
  int state = radio.receive(rx);

  if (state == RADIOLIB_ERR_NONE && rx.length() > 0) {
    lastRssi = radio.getRSSI();
    lastSnr = radio.getSNR();
    handleLoRaFrame(rx);
  }
}

String getFramePart(const String &s, int index) {
  int current = 0;
  int start = 0;

  for (int i = 0; i <= s.length(); i++) {
    if (i == s.length() || s.charAt(i) == '|') {
      if (current == index) {
        return s.substring(start, i);
      }
      current++;
      start = i + 1;
    }
  }

  return "";
}

void handleLoRaFrame(const String &frame) {
  String key = getFramePart(frame, 0);
  String to = getFramePart(frame, 1);
  String from = getFramePart(frame, 2);
  String cmd = getFramePart(frame, 3);
  String value = getFramePart(frame, 4);
  String msgId = getFramePart(frame, 5);

  if (cfg.requireLoraKey && !constantTimeEquals(key, String(LORA_SHARED_KEY))) return;

  if (to != DEVICE_ID && to != "ALL" && to != "BROADCAST") return;
  if (from == DEVICE_ID) return;

  sendLoRaFrame(from, "ACK", msgId);

  cmd.trim();
  value.trim();

  Serial.print("[LORA] ");
  Serial.print(from);
  Serial.print(" -> ");
  Serial.print(cmd);
  Serial.print(" = ");
  Serial.println(value);

  if (cmd == "STATUS_REQUEST") {
    sendLoRaStatus();
  }

  else if (cmd == "PING") {
    sendLoRaFrame(from, "PONG", DEVICE_ID);
  }

  else if (cmd == "RESET") {
    resetRuntime(true);
    showOverlay("REMOTE RESET", 1500);
  }

  else if (cmd == "ENABLE") {
    if (deviceState == STATE_ADMIN_DISABLED) resetRuntime(true);
    showOverlay("REMOTE ENABLE", 1500);
  }

  else if (cmd == "DISABLE") {
    transitionTo(STATE_ADMIN_DISABLED);
    showOverlay("REMOTE DISABLE", 1500);
  }

  else if (cmd == "START") {
    if (deviceState == STATE_STANDBY || deviceState == STATE_IDLE || deviceState == STATE_WAIT_PREREQ) {
      if (prereqArmOk()) transitionTo(STATE_ACTIVE);
      else transitionTo(STATE_WAIT_PREREQ);
    }
  }

  else if (cmd == "OBJECTIVE_COMPLETE") {
    if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
      transitionTo(STATE_DISARMED);
    }
  }

  else if (cmd == "MISSION_FAIL") {
    if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
      transitionTo(STATE_MISSION_FAILED);
    }
  }

  else if (cmd == "SET_TIMER") {
    int sec = value.toInt();
    if (sec >= 10 && sec <= 7200) {
      cfg.timerSeconds = sec;
      saveConfig();
      timerRemainMs = (long)cfg.timerSeconds * 1000;
      showOverlay("TIMER SET", 1500);
      sendLoRaStatus();
    }
  }

  else if (cmd == "SET_PROFILE") {
    int p = value.toInt();
    if (p >= 0 && p <= PROFILE_PAYLOAD_LINK) {
      applyProfile((GameProfile)p);
      saveConfig();
      resetRuntime(true);
      showOverlay("PROFILE SET", 1500);
    }
  }

  else if (cmd == "SET_ARM_CODE") {
    if (value.length() > 0 && value.length() < 16) {
      value.toCharArray(cfg.armCode, sizeof(cfg.armCode));
      saveConfig();
      showOverlay("ARM CODE SET", 1500);
    }
  }

  else if (cmd == "SET_DISARM_CODE") {
    if (value.length() > 0 && value.length() < 16) {
      value.toCharArray(cfg.disarmCode, sizeof(cfg.disarmCode));
      saveConfig();
      showOverlay("DISARM CODE SET", 1500);
    }
  }
}

void loopHeartbeat() {
  if (millis() - lastHeartbeatMs < HEARTBEAT_MS) return;
  lastHeartbeatMs = millis();
  sendLoRaStatus();

  if (batteryPercent() <= 20 && batteryPercent() > 0) {
    playMp3(TRACK_POWER_LOW);
    showOverlay("LOW BATTERY", 1500);
  }
}

// =============================================================================
// WEB
// =============================================================================

String htmlEscape(String s) {
  s.replace("&", "&amp;");
  s.replace("<", "&lt;");
  s.replace(">", "&gt;");
  s.replace("\"", "&quot;");
  s.replace("'", "&#39;");
  return s;
}

String buildWebPage() {
  String h;
  h.reserve(9000);

  h += F("<!DOCTYPE html><html><head><meta charset='UTF-8'>");
  h += F("<meta name='viewport' content='width=device-width,initial-scale=1'>");
  h += F("<title>CERBERUS OS</title>");
  h += F("<style>");
  h += F("body{background:#070707;color:#00ff66;font-family:monospace;max-width:620px;margin:auto;padding:16px}");
  h += F("h1{text-align:center;color:#ff3333;letter-spacing:3px;margin-bottom:0}");
  h += F(".sub{text-align:center;color:#777;margin-top:4px}");
  h += F(".box{border:1px solid #333;background:#101010;padding:10px;margin:12px 0}");
  h += F("h2{color:#ffff66;border-bottom:1px solid #333;padding-bottom:4px;margin-top:24px}");
  h += F("label{display:block;margin-top:12px;color:#aaa;font-size:12px}");
  h += F("input,select{width:100%;box-sizing:border-box;background:#151515;color:#00ff66;border:1px solid #00ff66;padding:8px;font-family:monospace}");
  h += F("input[type=checkbox]{width:auto;margin-right:8px}");
  h += F("button{width:100%;padding:12px;border:0;color:white;background:#990000;margin-top:12px;font-family:monospace;letter-spacing:2px}");
  h += F(".green{background:#006600}.grey{background:#333}.orange{background:#a06000}.row{display:flex;gap:8px}.row form{flex:1}");
  h += F("</style></head><body>");

  h += F("<h1>CERBERUS OS</h1>");
  h += F("<p class='sub'>");
  h += DEVICE_ID;
  h += F(" | v");
  h += FW_VERSION;
  h += F("</p>");

  h += F("<div class='box'>");
  h += F("<b>STATE:</b> ");
  h += stateLabel();
  h += F("<br><b>PROFILE:</b> ");
  h += profileLabel();
  h += F("<br><b>THEME:</b> ");
  h += themeLabel();
  h += F("<br><b>TIME:</b> ");
  h += formatTime(timerRemainMs);
  h += F("<br><b>PHASE:</b> ");
  h += phaseLabel();
  h += F("<br><b>MODULE:</b> ");
  h += dummyConnected ? "CONNECTED" : "DISCONNECTED";
  h += F("<br><b>BATTERY:</b> ");
  h += batteryPercent();
  h += F("%<br><b>LORA:</b> ");
  h += loraReady ? "READY" : "OFFLINE";
  h += F("</div>");

  h += F("<form method='POST' action='/save'>");

  h += F("<h2>PROFILE</h2>");
  h += F("<label>Game profile</label><select name='profile'>");
  for (int i = 0; i <= PROFILE_PAYLOAD_LINK; i++) {
    GameProfile old = cfg.profile;
    cfg.profile = (GameProfile)i;
    h += F("<option value='");
    h += i;
    h += F("'");
    if ((int)old == i) h += F(" selected");
    h += F(">");
    h += profileLabel();
    h += F("</option>");
    cfg.profile = old;
  }
  h += F("</select>");

  h += F("<label>Theme</label><select name='theme'>");
  for (int i = 0; i <= THEME_DATA_TERMINAL; i++) {
    ObjectiveTheme old = cfg.theme;
    cfg.theme = (ObjectiveTheme)i;
    h += F("<option value='");
    h += i;
    h += F("'");
    if ((int)old == i) h += F(" selected");
    h += F(">");
    h += themeLabel();
    h += F("</option>");
    cfg.theme = old;
  }
  h += F("</select>");

  h += F("<h2>TIMER</h2>");
  h += F("<label>Timer seconds</label><input type='number' name='timer' min='10' max='7200' value='");
  h += cfg.timerSeconds;
  h += F("'>");

  h += F("<label>Phase 2 percent remaining</label><input type='number' name='ph2' min='10' max='90' value='");
  h += cfg.phase2Percent;
  h += F("'>");

  h += F("<label>Phase 3 percent remaining</label><input type='number' name='ph3' min='5' max='80' value='");
  h += cfg.phase3Percent;
  h += F("'>");

  h += F("<h2>ARM / DISARM</h2>");
  h += F("<label>Arm method</label><select name='armM'>");
  for (int i = 0; i <= ARM_DUMMY_AND_CODE; i++) {
    ArmMethod old = cfg.armMethod;
    cfg.armMethod = (ArmMethod)i;
    h += F("<option value='");
    h += i;
    h += F("'");
    if ((int)old == i) h += F(" selected");
    h += F(">");
    h += armMethodLabel();
    h += F("</option>");
    cfg.armMethod = old;
  }
  h += F("</select>");

  h += F("<label>Disarm method</label><select name='disM'>");
  for (int i = 0; i <= DISARM_MULTI_STAGE; i++) {
    DisarmMethod old = cfg.disarmMethod;
    cfg.disarmMethod = (DisarmMethod)i;
    h += F("<option value='");
    h += i;
    h += F("'");
    if ((int)old == i) h += F(" selected");
    h += F(">");
    h += disarmMethodLabel();
    h += F("</option>");
    cfg.disarmMethod = old;
  }
  h += F("</select>");

  h += F("<label>Arm code</label><input name='armCode' maxlength='15' value='");
  h += htmlEscape(cfg.armCode);
  h += F("'>");

  h += F("<label>Disarm code</label><input name='disCode' maxlength='15' value='");
  h += htmlEscape(cfg.disarmCode);
  h += F("'>");

  h += F("<label>Red hold time ms</label><input type='number' name='holdMs' min='500' max='10000' value='");
  h += cfg.holdRedMs;
  h += F("'>");

  h += F("<h2>MODULE LOOP</h2>");
  h += F("<label><input type='checkbox' name='dumArm'");
  if (cfg.requireDummyToArm) h += F(" checked");
  h += F(">Require module to arm</label>");

  h += F("<label><input type='checkbox' name='dumDis'");
  if (cfg.requireDummyToDisarm) h += F(" checked");
  h += F(">Require module to disarm</label>");

  h += F("<label><input type='checkbox' name='dumAlert'");
  if (cfg.alertIfDummyRemovedActive) h += F(" checked");
  h += F(">Alert if module removed while active</label>");

  h += F("<h2>WRONG CODE PENALTY</h2>");
  h += F("<label>Penalty</label><select name='penalty'>");
  for (int i = 0; i <= PENALTY_FORCE_PHASE_3; i++) {
    WrongCodePenalty old = cfg.wrongPenalty;
    cfg.wrongPenalty = (WrongCodePenalty)i;
    h += F("<option value='");
    h += i;
    h += F("'");
    if ((int)old == i) h += F(" selected");
    h += F(">");
    h += penaltyLabel();
    h += F("</option>");
    cfg.wrongPenalty = old;
  }
  h += F("</select>");

  h += F("<label><input type='checkbox' name='lockout'");
  if (cfg.lockoutOnWrongCode) h += F(" checked");
  h += F(">Enable lockout</label>");

  h += F("<label>Max wrong attempts</label><input type='number' name='maxWrong' min='1' max='10' value='");
  h += cfg.maxWrongAttempts;
  h += F("'>");

  h += F("<label>Lockout seconds</label><input type='number' name='lockSecs' min='5' max='3600' value='");
  h += cfg.lockoutDurationSecs;
  h += F("'>");

  h += F("<label>Time penalty seconds</label><input type='number' name='penSecs' min='5' max='600' value='");
  h += cfg.wrongCodeTimePenaltySecs;
  h += F("'>");

  h += F("<h2>AUDIO / LORA</h2>");
  h += F("<label><input type='checkbox' name='audio'");
  if (cfg.enableAudio) h += F(" checked");
  h += F(">Enable audio</label>");

  h += F("<label>MP3 volume 0-30</label><input type='number' name='vol' min='0' max='30' value='");
  h += cfg.mp3Volume;
  h += F("'>");

  h += F("<label><input type='checkbox' name='lora'");
  if (cfg.enableLoRa) h += F(" checked");
  h += F(">Enable LoRa</label>");

  h += F("<label><input type='checkbox' name='loraKey'");
  if (cfg.requireLoraKey) h += F(" checked");
  h += F(">Require LoRa shared key</label>");

  h += F("<h2>ADMIN</h2>");
  h += F("<label>Admin PIN for quick actions</label><input name='adminPin' maxlength='11' value='");
  h += htmlEscape(cfg.adminPin);
  h += F("'>");

  h += F("<button type='submit'>SAVE CONFIG</button>");
  h += F("</form>");

  h += F("<h2>QUICK ACTIONS</h2>");
  h += F("<form method='POST' action='/arm'><label>Admin PIN</label><input name='pin'><button>START OBJECTIVE</button></form>");
  h += F("<form method='POST' action='/disarm'><label>Admin PIN</label><input name='pin'><button class='green'>COMPLETE OBJECTIVE</button></form>");
  h += F("<form method='POST' action='/reset'><label>Admin PIN</label><input name='pin'><button class='grey'>RESET</button></form>");
  h += F("<form method='POST' action='/disable'><label>Admin PIN</label><input name='pin'><button class='orange'>ADMIN DISABLE</button></form>");

  h += F("</body></html>");
  return h;
}

bool adminPinOk() {
  if (!webServer.hasArg("pin")) return false;
  return constantTimeEquals(webServer.arg("pin"), String(cfg.adminPin));
}

void handleRoot() {
  webServer.send(200, "text/html", buildWebPage());
}

void handleSave() {
  if (webServer.hasArg("profile")) {
    int p = webServer.arg("profile").toInt();
    if (p >= 0 && p <= PROFILE_PAYLOAD_LINK) {
      applyProfile((GameProfile)p);
    }
  }

  if (webServer.hasArg("theme")) {
    int v = webServer.arg("theme").toInt();
    if (v >= 0 && v <= THEME_DATA_TERMINAL) cfg.theme = (ObjectiveTheme)v;
  }

  if (webServer.hasArg("armM")) {
    int v = webServer.arg("armM").toInt();
    if (v >= 0 && v <= ARM_DUMMY_AND_CODE) cfg.armMethod = (ArmMethod)v;
  }

  if (webServer.hasArg("disM")) {
    int v = webServer.arg("disM").toInt();
    if (v >= 0 && v <= DISARM_MULTI_STAGE) cfg.disarmMethod = (DisarmMethod)v;
  }

  if (webServer.hasArg("penalty")) {
    int v = webServer.arg("penalty").toInt();
    if (v >= 0 && v <= PENALTY_FORCE_PHASE_3) cfg.wrongPenalty = (WrongCodePenalty)v;
  }

  if (webServer.hasArg("armCode")) {
    String v = webServer.arg("armCode");
    v.trim();
    if (v.length() > 0 && v.length() < 16) v.toCharArray(cfg.armCode, sizeof(cfg.armCode));
  }

  if (webServer.hasArg("disCode")) {
    String v = webServer.arg("disCode");
    v.trim();
    if (v.length() > 0 && v.length() < 16) v.toCharArray(cfg.disarmCode, sizeof(cfg.disarmCode));
  }

  if (webServer.hasArg("adminPin")) {
    String v = webServer.arg("adminPin");
    v.trim();
    if (v.length() > 0 && v.length() < 12) v.toCharArray(cfg.adminPin, sizeof(cfg.adminPin));
  }

  if (webServer.hasArg("timer")) cfg.timerSeconds = webServer.arg("timer").toInt();
  if (webServer.hasArg("holdMs")) cfg.holdRedMs = webServer.arg("holdMs").toInt();
  if (webServer.hasArg("ph2")) cfg.phase2Percent = webServer.arg("ph2").toInt();
  if (webServer.hasArg("ph3")) cfg.phase3Percent = webServer.arg("ph3").toInt();

  cfg.requireDummyToArm = webServer.hasArg("dumArm");
  cfg.requireDummyToDisarm = webServer.hasArg("dumDis");
  cfg.alertIfDummyRemovedActive = webServer.hasArg("dumAlert");

  cfg.lockoutOnWrongCode = webServer.hasArg("lockout");
  if (webServer.hasArg("maxWrong")) cfg.maxWrongAttempts = webServer.arg("maxWrong").toInt();
  if (webServer.hasArg("lockSecs")) cfg.lockoutDurationSecs = webServer.arg("lockSecs").toInt();
  if (webServer.hasArg("penSecs")) cfg.wrongCodeTimePenaltySecs = webServer.arg("penSecs").toInt();

  cfg.enableAudio = webServer.hasArg("audio");
  if (webServer.hasArg("vol")) cfg.mp3Volume = webServer.arg("vol").toInt();

  cfg.enableLoRa = webServer.hasArg("lora");
  cfg.requireLoraKey = webServer.hasArg("loraKey");

  saveConfig();
  resetRuntime(true);
  showOverlay("CONFIG SAVED", 1500);

  webServer.sendHeader("Location", "/");
  webServer.send(302, "text/plain", "Saved");
}

void handleActionArm() {
  if (!adminPinOk()) {
    webServer.send(403, "text/plain", "Bad PIN");
    return;
  }

  if (prereqArmOk()) transitionTo(STATE_ACTIVE);
  else transitionTo(STATE_WAIT_PREREQ);

  webServer.sendHeader("Location", "/");
  webServer.send(302, "text/plain", "");
}

void handleActionDisarm() {
  if (!adminPinOk()) {
    webServer.send(403, "text/plain", "Bad PIN");
    return;
  }

  if (deviceState == STATE_ACTIVE || deviceState == STATE_DISARMING) {
    transitionTo(STATE_DISARMED);
  }

  webServer.sendHeader("Location", "/");
  webServer.send(302, "text/plain", "");
}

void handleActionReset() {
  if (!adminPinOk()) {
    webServer.send(403, "text/plain", "Bad PIN");
    return;
  }

  resetRuntime(true);

  webServer.sendHeader("Location", "/");
  webServer.send(302, "text/plain", "");
}

void handleActionDisable() {
  if (!adminPinOk()) {
    webServer.send(403, "text/plain", "Bad PIN");
    return;
  }

  transitionTo(STATE_ADMIN_DISABLED);

  webServer.sendHeader("Location", "/");
  webServer.send(302, "text/plain", "");
}

void handleStatusJson() {
  String json = "{";
  json += "\"id\":\"" + String(DEVICE_ID) + "\",";
  json += "\"name\":\"" + String(DEVICE_NAME) + "\",";
  json += "\"fw\":\"" + String(FW_VERSION) + "\",";
  json += "\"state\":\"" + stateLabel() + "\",";
  json += "\"theme\":\"" + themeLabel() + "\",";
  json += "\"profile\":\"" + profileLabel() + "\",";
  json += "\"phase\":" + String((int)devicePhase) + ",";
  json += "\"timer_ms\":" + String(timerRemainMs) + ",";
  json += "\"dummy\":" + String(dummyConnected ? "true" : "false") + ",";
  json += "\"battery\":" + String(batteryPercent()) + ",";
  json += "\"lora\":" + String(loraReady ? "true" : "false");
  json += "}";

  webServer.send(200, "application/json", json);
}

void setupWebServer() {
  webServer.on("/", HTTP_GET, handleRoot);
  webServer.on("/save", HTTP_POST, handleSave);
  webServer.on("/arm", HTTP_POST, handleActionArm);
  webServer.on("/disarm", HTTP_POST, handleActionDisarm);
  webServer.on("/reset", HTTP_POST, handleActionReset);
  webServer.on("/disable", HTTP_POST, handleActionDisable);
  webServer.on("/status", HTTP_GET, handleStatusJson);

  webServer.begin();
}

void loopWeb() {
  webServer.handleClient();
}

// =============================================================================
// UTILITY
// =============================================================================

bool constantTimeEquals(const String &a, const String &b) {
  if (a.length() != b.length()) return false;

  uint8_t result = 0;
  for (unsigned int i = 0; i < a.length(); i++) {
    result |= a.charAt(i) ^ b.charAt(i);
  }

  return result == 0;
}

int batteryPercent() {
#if USE_BATTERY_ADC
  int raw = analogRead(PIN_BATTERY_ADC);
  int pct = map(raw, 1800, 3000, 0, 100);
  return constrain(pct, 0, 100);
#else
  return 100;
#endif
}

// =============================================================================
// SETUP
// =============================================================================

void setupPins() {
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_ARM_SWITCH, INPUT_PULLUP);
  pinMode(PIN_RED_BUTTON, INPUT_PULLUP);
  pinMode(PIN_DUMMY_PROP, INPUT_PULLUP);

  buzzerWrite(false);
}

void setupDisplays() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);

  oled.begin();
  oled.clearBuffer();
  oled.setFont(u8g2_font_7x13B_tf);
  oled.drawStr(11, 24, "CERBERUS OS");
  oled.setFont(u8g2_font_6x10_tf);
  oled.drawStr(23, 42, "AOJ Objective Core");
  oled.drawStr(45, 56, "v" FW_VERSION);
  oled.sendBuffer();

  seg7.begin(SEG7_ADDR);
  seg7.setBrightness(12);
  seg7.clear();
  seg7.writeDisplay();
}

void setupAudio() {
  mp3Serial.begin(9600, SERIAL_8N1, PIN_MP3_RX, PIN_MP3_TX);
  delay(500);

  if (mp3Player.begin(mp3Serial, false, true)) {
    mp3Ready = true;
    mp3Player.volume(cfg.mp3Volume);
    Serial.println("[MP3] Ready");
  } else {
    mp3Ready = false;
    Serial.println("[MP3] Not found");
  }
}

void setupWiFi() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD);

  Serial.print("[WIFI] AP: ");
  Serial.print(AP_SSID);
  Serial.print(" IP: ");
  Serial.println(WiFi.softAPIP());

  setupWebServer();
}

void setupLoRa() {
  if (!cfg.enableLoRa) {
    loraReady = false;
    return;
  }

  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);

  int result = radio.begin(
    LORA_FREQUENCY,
    LORA_BANDWIDTH,
    LORA_SF,
    LORA_CR,
    RADIOLIB_SX126X_SYNC_WORD_PRIVATE,
    LORA_POWER,
    8,
    1.6,
    false
  );

  if (result == RADIOLIB_ERR_NONE) {
    loraReady = true;
    Serial.println("[LORA] Ready");
  } else {
    loraReady = false;
    Serial.print("[LORA] Failed: ");
    Serial.println(result);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println();
  Serial.println("[CERBERUS] Booting");

  setDefaultConfig();
  loadConfig();

  setupPins();
  setupDisplays();
  setupAudio();
  setupWiFi();
  setupLoRa();

  dummyStable = dummyRaw();
  dummyLastRaw = dummyStable;
  dummyConnected = dummyStable;
  dummyChangedMs = millis();

  timerRemainMs = (long)cfg.timerSeconds * 1000;

  startBeepPattern(BEEP_BOOT);
  playMp3(TRACK_BOOT);

  if (cfg.requireDummyToArm && !dummyConnected) {
    deviceState = STATE_WAIT_PREREQ;
  } else {
    deviceState = STATE_STANDBY;
  }

  stateEnteredMs = millis();

  showOverlay("READY", 1500);
  sendLoRaStatus();

  Serial.println("[CERBERUS] Ready");
}

// =============================================================================
// LOOP
// =============================================================================

void loop() {
  loopWeb();
  loopLoRa();
  loopHeartbeat();

  loopDummy();
  loopInputs();
  loopCountdown();
  loopPhase();
  loopLockout();

  loopBuzzer();

  updateOled();
  updateSeg7();
}