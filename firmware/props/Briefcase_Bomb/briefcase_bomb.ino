#include <AOJ_Core.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>
#include <U8g2lib.h>
#include <DFRobotDFPlayerMini.h>

// =====================================================
// AOJ OVERRIDE CASE - SAFE AIRSOFT ELECTRONIC PROP
// Heltec WiFi LoRa 32 V3 / ESP32-S3
//
// Relay output is for horn/siren/lamp/game signal only.
// Do not connect to pyrotechnics, ignition devices,
// gas systems, pressure systems, or anything dangerous.
// =====================================================

// =====================================================
// USER SETTINGS
// =====================================================

#define DEVICE_ID "CASE-001"
#define PROP_TYPE "Briefcase Bomb"
#define FW_VERSION "1.1.0"

// LoRa is managed by AOJ_Core.h

// Relay behaviour
const bool RELAY_ACTIVE_LOW = true;

// Horn/siren relay active time after triggered
const unsigned long HORN_DURATION_MS = 10000;

// Shutdown drama duration
const unsigned long SHUTDOWN_DURATION_MS = 12000;

// =====================================================
// PIN MAP
// =====================================================

// LoRa pins configured in AOJ_Core.h for Heltec V3

// Shared I2C bus for OLED and 20x4 LCD
#define I2C_SDA 17
#define I2C_SCL 18

// LCD I2C address.
// Common values are 0x27 or 0x3F.
#define LCD_ADDR 0x27

// DFPlayer Mini serial pins
#define MP3_RX_PIN 15  // ESP32 RX, connect to DFPlayer TX
#define MP3_TX_PIN 16  // ESP32 TX, connect to DFPlayer RX through resistor

// Inputs
#define BUTTON_NEXT_PIN   33
#define BUTTON_SELECT_PIN 34
#define ARM_SWITCH_PIN    35
#define USB_DETECT_PIN    36
#define POT_PIN           37

// LEDs
#define LED_GREEN  39
#define LED_YELLOW 40
#define LED_RED    41

// Buzzer
#define BUZZER_PIN 42

// Horn relay
#define RELAY_PIN 47

// 4x3 keypad pins
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

// =====================================================
// OBJECTS
// =====================================================

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// If your OLED is SH1106 instead of SSD1309, replace this line with:
// U8G2_SH1106_128X64_NONAME_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);
U8G2_SSD1309_128X64_NONAME0_F_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);

LiquidCrystal_I2C lcd(LCD_ADDR, 20, 4);

// AOJ Core objects
AojLoRa lora;
AojWiFi wifi;

HardwareSerial mp3Serial(1);
DFRobotDFPlayerMini mp3;
bool mp3Ready = false;

// =====================================================
// SAVED SETTINGS
// =====================================================

String armCode = "1975";
String securityCode = "2468";

unsigned long configuredStartSeconds = 10UL * 60UL;

int lowDisarmPercent = 10;
int highTriggerPercent = 90;
int abortShutdownPercent = 25;

int maxMistakes = 4;

bool allowPowerUpTrigger = true;

int mp3Volume = 24;

// =====================================================
// GAME STATE
// =====================================================

enum GameState {
  STATE_SAFE,
  STATE_ARMING_CODE,
  STATE_ARMED_NEED_USB,
  STATE_WAIT_SECURITY_CODE,
  STATE_POWER_CONTROL,
  STATE_SHUTDOWN_SEQUENCE,
  STATE_DISARMED,
  STATE_TRIGGERED
};

GameState state = STATE_SAFE;

float remainingSeconds = 0;
float timerRate = 1.0;

int mistakeCount = 0;
String codeInput = "";

bool armingSwitchLatched = false;
bool overrideKeyAccepted = false;
bool securityAccepted = false;
bool hornActive = false;

unsigned long hornStartedAt = 0;
unsigned long lastTimerUpdate = 0;
unsigned long lastBeep = 0;
unsigned long lastDisplayUpdate = 0;
unsigned long lastStatusSend = 0;
unsigned long lastButtonRead = 0;
unsigned long shutdownStartedAt = 0;
unsigned long lastShutdownStep = 0;

bool previousNextButton = HIGH;
bool previousSelectButton = HIGH;

int displayPage = 0;
int shutdownFrame = 0;

// =====================================================
// BASIC HELPERS
// =====================================================

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
    beep(70);
    delay(60);
  }
}

void successNoise() {
  beep(100);
  delay(70);
  beep(100);
  delay(70);
  beep(260);
}

void alarmNoise() {
  for (int i = 0; i < 8; i++) {
    beep(90);
    delay(60);
  }
}

void playMp3(int track) {
  if (!mp3Ready) return;
  mp3.playMp3Folder(track);
}

String stateName() {
  switch (state) {
    case STATE_SAFE: return "SAFE";
    case STATE_ARMING_CODE: return "ARMING_CODE";
    case STATE_ARMED_NEED_USB: return "ARMED_NEED_USB";
    case STATE_WAIT_SECURITY_CODE: return "WAIT_SECURITY_CODE";
    case STATE_POWER_CONTROL: return "POWER_CONTROL";
    case STATE_SHUTDOWN_SEQUENCE: return "SHUTDOWN_SEQUENCE";
    case STATE_DISARMED: return "DISARMED";
    case STATE_TRIGGERED: return "TRIGGERED";
    default: return "UNKNOWN";
  }
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

int readPowerPercent() {
  int raw = analogRead(POT_PIN);
  int percent = map(raw, 0, 4095, 0, 100);

  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;

  return percent;
}

float readPowerVoltage() {
  int raw = analogRead(POT_PIN);
  return (raw / 4095.0) * 3.3;
}

bool usbKeyInserted() {
  return digitalRead(USB_DETECT_PIN) == LOW;
}

bool armSwitchOn() {
  return digitalRead(ARM_SWITCH_PIN) == LOW;
}

String maskedInput() {
  String out = "";
  for (unsigned int i = 0; i < codeInput.length(); i++) {
    out += "*";
  }
  return out;
}

// =====================================================
// SETTINGS STORAGE
// =====================================================

void loadSettings() {
  prefs.begin("aojcase", false);

  armCode = prefs.getString("arm", "1975");
  securityCode = prefs.getString("sec", "2468");

  configuredStartSeconds = prefs.getULong("timer", 600);

  lowDisarmPercent = prefs.getInt("low", 10);
  highTriggerPercent = prefs.getInt("high", 90);
  abortShutdownPercent = prefs.getInt("abort", 25);

  maxMistakes = prefs.getInt("mistakes", 4);
  allowPowerUpTrigger = prefs.getBool("allowTrig", true);

  mp3Volume = prefs.getInt("volume", 24);

  if (configuredStartSeconds < 30) configuredStartSeconds = 30;
  if (configuredStartSeconds > 3600) configuredStartSeconds = 3600;

  if (lowDisarmPercent < 1) lowDisarmPercent = 1;
  if (lowDisarmPercent > 40) lowDisarmPercent = 10;

  if (highTriggerPercent < 60) highTriggerPercent = 90;
  if (highTriggerPercent > 100) highTriggerPercent = 100;

  if (abortShutdownPercent <= lowDisarmPercent) abortShutdownPercent = lowDisarmPercent + 15;
  if (abortShutdownPercent > 60) abortShutdownPercent = 25;

  if (maxMistakes < 1) maxMistakes = 4;
  if (maxMistakes > 10) maxMistakes = 4;

  if (mp3Volume < 0) mp3Volume = 0;
  if (mp3Volume > 30) mp3Volume = 30;

  prefs.end();
}

void saveSettings() {
  prefs.begin("aojcase", false);

  prefs.putString("arm", armCode);
  prefs.putString("sec", securityCode);

  prefs.putULong("timer", configuredStartSeconds);

  prefs.putInt("low", lowDisarmPercent);
  prefs.putInt("high", highTriggerPercent);
  prefs.putInt("abort", abortShutdownPercent);

  prefs.putInt("mistakes", maxMistakes);
  prefs.putBool("allowTrig", allowPowerUpTrigger);

  prefs.putInt("volume", mp3Volume);

  prefs.end();
}

// =====================================================
// LORA
// =====================================================

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

void checkLora() {
  String incoming = "";
  int result = radio.receive(incoming, 5);

  if (result == RADIOLIB_ERR_NONE) {
    incoming.trim();

    if (packetMatchesThisUnit(incoming)) {
      if (incoming.indexOf("REMOTE_TRIGGER:" + String(REMOTE_KEY)) >= 0) {
        // This means game horn activation / admin-triggered failure.
        state = STATE_TRIGGERED;
        hornActive = true;
        hornStartedAt = millis();
        setRelay(true);
        playMp3(12);
        sendLoraMessage("DETONATED:REMOTE");
      }

      if (incoming.indexOf("REMOTE_DISARM:" + String(REMOTE_KEY)) >= 0) {
        state = STATE_DISARMED;
        hornActive = false;
        setRelay(false);
        playMp3(11);
        sendLoraMessage("DISARMED:REMOTE");
      }

      if (incoming.indexOf("REMOTE_RESET:" + String(REMOTE_KEY)) >= 0) {
        state = STATE_SAFE;
        sendLoraMessage("RESET:REMOTE");
      }

      if (incoming.indexOf("STATUS_REQUEST") >= 0) {
        sendLoraMessage("STATUS:" + stateName() + ":TIME:" + formatTime(remainingSeconds));
      }
    }
  }

  radio.startReceive();
}

// =====================================================
// GAME ACTIONS
// =====================================================

void resetRuntimeFlags() {
  timerRate = 1.0;
  mistakeCount = 0;
  codeInput = "";
  overrideKeyAccepted = false;
  securityAccepted = false;
  hornActive = false;
  shutdownFrame = 0;
  displayPage = 0;
}

void resetToSafe() {
  state = STATE_SAFE;

  remainingSeconds = configuredStartSeconds;
  armingSwitchLatched = false;

  resetRuntimeFlags();

  setRelay(false);
  buzzerOff();

  sendLoraMessage("SAFE");
}

void beginArmingCodeEntry() {
  state = STATE_ARMING_CODE;
  codeInput = "";
  playMp3(2);
  beep(120);
}

void armUnit() {
  state = STATE_ARMED_NEED_USB;

  remainingSeconds = configuredStartSeconds;
  lastTimerUpdate = millis();
  lastBeep = millis();

  resetRuntimeFlags();
  armingSwitchLatched = true;

  playMp3(3);
  beep(250);

  sendLoraMessage("ARMED");
}

void disarmUnit(String method) {
  state = STATE_DISARMED;
  hornActive = false;

  setRelay(false);
  buzzerOff();

  playMp3(11);
  successNoise();

  sendLoraMessage("DISARMED:" + method);
}

void triggerHorn(String reason) {
  if (state == STATE_TRIGGERED) return;

  state = STATE_TRIGGERED;
  hornActive = true;
  hornStartedAt = millis();

  setRelay(true);
  playMp3(12);
  alarmNoise();

  sendLoraMessage("DETONATED:" + reason);
}

void applyMistakePenalty(String reason) {
  if (state == STATE_SAFE || state == STATE_DISARMED || state == STATE_TRIGGERED) return;

  mistakeCount++;

  playMp3(7);
  errorNoise();

  sendLoraMessage("WRONG_CODE_" + String(mistakeCount) + ":" + reason);

  if (mistakeCount == 1) {
    timerRate = 1.5;
  } else if (mistakeCount == 2) {
    remainingSeconds *= 0.75;
  } else if (mistakeCount == 3) {
    timerRate = 2.5;
  }

  if (mistakeCount >= maxMistakes) {
    triggerHorn("TOO_MANY_MISTAKES");
  }
}

void startShutdownSequence() {
  state = STATE_SHUTDOWN_SEQUENCE;
  shutdownStartedAt = millis();
  lastShutdownStep = millis();
  shutdownFrame = 0;
  codeInput = "";

  playMp3(9);
  sendLoraMessage("POWER_DOWN_STARTED");
  beep(200);
}

void abortShutdown() {
  state = STATE_POWER_CONTROL;
  shutdownFrame = 0;

  playMp3(10);
  errorNoise();

  sendLoraMessage("SHUTDOWN_ABORTED");
  applyMistakePenalty("SHUTDOWN_ABORTED_POWER_RISE");
}

// =====================================================
// INPUT HANDLING
// =====================================================

void handleArmSwitch() {
  if (state != STATE_SAFE) return;

  if (armSwitchOn() && !armingSwitchLatched) {
    beginArmingCodeEntry();
  }
}

void handleButtons() {
  if (millis() - lastButtonRead < 60) return;
  lastButtonRead = millis();

  bool nextNow = digitalRead(BUTTON_NEXT_PIN);
  bool selectNow = digitalRead(BUTTON_SELECT_PIN);

  if (previousNextButton == HIGH && nextNow == LOW) {
    displayPage++;
    if (displayPage > 2) displayPage = 0;
    beep(40);
  }

  if (previousSelectButton == HIGH && selectNow == LOW) {
    if (state == STATE_POWER_CONTROL) {
      int p = readPowerPercent();

      if (p <= lowDisarmPercent) {
        startShutdownSequence();
      } else if (p >= highTriggerPercent) {
        if (allowPowerUpTrigger) {
          triggerHorn("POWER_UP_CONFIRMED_BUTTON");
        } else {
          applyMistakePenalty("POWER_TOO_HIGH");
        }
      } else {
        applyMistakePenalty("POWER_UNSTABLE_SELECT");
      }
    } else {
      beep(40);
    }
  }

  previousNextButton = nextNow;
  previousSelectButton = selectNow;
}

void handleUsbKey() {
  if (state != STATE_ARMED_NEED_USB) return;

  if (usbKeyInserted()) {
    overrideKeyAccepted = true;
    state = STATE_WAIT_SECURITY_CODE;
    codeInput = "";

    playMp3(4);
    successNoise();

    sendLoraMessage("USB_INSERTED");
  }
}

void handleKeypad() {
  char key = keypad.getKey();

  if (!key) return;

  if (key >= '0' && key <= '9') {
    if (codeInput.length() < 10) {
      codeInput += key;
      beep(25);
    }
    return;
  }

  if (key == '*') {
    codeInput = "";
    beep(50);
    return;
  }

  if (key == '#') {
    if (state == STATE_ARMING_CODE) {
      if (codeInput == armCode) {
        armUnit();
      } else {
        codeInput = "";
        playMp3(7);
        errorNoise();
        state = STATE_SAFE;
        armingSwitchLatched = false;
        sendLoraMessage("ARM_CODE_FAILED");
      }
      return;
    }

    if (state == STATE_ARMED_NEED_USB) {
      codeInput = "";
      playMp3(7);
      errorNoise();
      sendLoraMessage("KEYPAD_LOCKED_USB_REQUIRED");
      return;
    }

    if (state == STATE_WAIT_SECURITY_CODE) {
      if (codeInput == securityCode) {
        securityAccepted = true;
        state = STATE_POWER_CONTROL;
        codeInput = "";

        playMp3(6);
        successNoise();
        delay(250);
        playMp3(8);

        sendLoraMessage("CODE_ACCEPTED");
      } else {
        codeInput = "";
        applyMistakePenalty("WRONG_SECURITY_CODE");
      }
      return;
    }

    if (state == STATE_POWER_CONTROL) {
      int p = readPowerPercent();

      if (p <= lowDisarmPercent) {
        startShutdownSequence();
      } else if (p >= highTriggerPercent) {
        if (allowPowerUpTrigger) {
          triggerHorn("POWER_UP_CONFIRMED_KEYPAD");
        } else {
          applyMistakePenalty("POWER_TOO_HIGH");
        }
      } else {
        applyMistakePenalty("POWER_UNSTABLE_KEYPAD");
      }
      return;
    }
  }
}

// =====================================================
// TIMER / HORN / STATUS
// =====================================================

void updateTimer() {
  if (
    state != STATE_ARMED_NEED_USB &&
    state != STATE_WAIT_SECURITY_CODE &&
    state != STATE_POWER_CONTROL &&
    state != STATE_SHUTDOWN_SEQUENCE
  ) {
    lastTimerUpdate = millis();
    return;
  }

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
    playMp3(13);
    triggerHorn("TIME_EXPIRED");
  }
}

void updateBeeps() {
  if (
    state != STATE_ARMED_NEED_USB &&
    state != STATE_WAIT_SECURITY_CODE &&
    state != STATE_POWER_CONTROL
  ) {
    return;
  }

  unsigned long now = millis();

  unsigned long interval = 1000;

  if (mistakeCount >= 1) interval = 650;
  if (mistakeCount >= 2) interval = 450;
  if (remainingSeconds <= 60) interval = 300;
  if (remainingSeconds <= 20) interval = 160;

  if (now - lastBeep >= interval) {
    lastBeep = now;
    beep(30);
  }
}

void updateHorn() {
  if (!hornActive) return;

  if (millis() - hornStartedAt >= HORN_DURATION_MS) {
    hornActive = false;
    setRelay(false);
  }
}



// =====================================================
// SHUTDOWN SEQUENCE
// =====================================================

void updateShutdownSequence() {
  if (state != STATE_SHUTDOWN_SEQUENCE) return;

  int p = readPowerPercent();

  if (!usbKeyInserted()) {
    abortShutdown();
    return;
  }

  if (p > abortShutdownPercent) {
    abortShutdown();
    return;
  }

  unsigned long elapsed = millis() - shutdownStartedAt;

  if (millis() - lastShutdownStep > 900) {
    lastShutdownStep = millis();
    shutdownFrame++;

    if (shutdownFrame == 2) playMp3(10);

    int toneDuration = 120 - (shutdownFrame * 6);
    if (toneDuration < 35) toneDuration = 35;

    beep(toneDuration);
  }

  if (elapsed >= SHUTDOWN_DURATION_MS) {
    disarmUnit("POWER_DOWN");
  }
}

// =====================================================
// LEDS
// =====================================================

void updateLeds() {
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

  if (state == STATE_SHUTDOWN_SEQUENCE) {
    digitalWrite(LED_GREEN, (millis() / 500) % 2);
    digitalWrite(LED_YELLOW, (millis() / 250) % 2);
    digitalWrite(LED_RED, (millis() / 120) % 2);
    return;
  }

  if (state == STATE_POWER_CONTROL) {
    int p = readPowerPercent();

    digitalWrite(LED_GREEN, p <= lowDisarmPercent ? HIGH : LOW);
    digitalWrite(LED_YELLOW, p > lowDisarmPercent && p < highTriggerPercent ? ((millis() / 300) % 2) : LOW);
    digitalWrite(LED_RED, p >= highTriggerPercent ? ((millis() / 120) % 2) : HIGH);
    return;
  }

  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, HIGH);

  if (state == STATE_WAIT_SECURITY_CODE || mistakeCount > 0 || remainingSeconds <= 60) {
    digitalWrite(LED_YELLOW, (millis() / 300) % 2);
  } else {
    digitalWrite(LED_YELLOW, LOW);
  }
}

// =====================================================
// DISPLAY HELPERS
// =====================================================

void lcdPrintLine(int row, String text) {
  lcd.setCursor(0, row);

  if (text.length() > 20) {
    text = text.substring(0, 20);
  }

  while (text.length() < 20) {
    text += " ";
  }

  lcd.print(text);
}

void drawOledSafe() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, "AOJ OVERRIDE CASE");
  oled.drawHLine(0, 15, 128);
  oled.drawStr(0, 32, "STATE: SAFE");
  oled.drawStr(0, 46, "Flip switch to arm");
  oled.drawStr(0, 60, "WiFi: 192.168.4.1");
}

void drawOledArming() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, "ARMING MODE");
  oled.drawHLine(0, 15, 128);
  oled.drawStr(0, 32, "ENTER STAFF CODE");
  String input = "CODE: " + maskedInput();
  oled.drawStr(0, 48, input.c_str());
  oled.drawStr(0, 62, "#=OK  *=CLEAR");
}

void drawOledNeedUsb() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, "AUTH BUS: LOCKED");
  oled.drawHLine(0, 15, 128);
  oled.drawStr(0, 31, "USB PORT: EMPTY");
  oled.drawStr(0, 45, "OVERRIDE REQUIRED");
  oled.drawStr(0, 60, "FIND FIELD KEY");
}

void drawOledSecurity() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, "OVERRIDE ACTIVE");
  oled.drawHLine(0, 15, 128);
  oled.drawStr(0, 31, "USB KEY: VALID");
  oled.drawStr(0, 45, "ENTER SECURITY CODE");
  String input = "INPUT: " + maskedInput();
  oled.drawStr(0, 60, input.c_str());
}

void drawOledPowerControl() {
  int p = readPowerPercent();
  float v = readPowerVoltage();

  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 10, "POWER CONTROL");
  oled.drawHLine(0, 13, 128);

  String line1 = "PWR: " + String(p) + "%  " + String(v, 2) + "V";
  oled.drawStr(0, 28, line1.c_str());

  if (p <= lowDisarmPercent) {
    oled.drawStr(0, 43, "STATUS: DOWN READY");
    oled.drawStr(0, 60, "PRESS # TO DISARM");
  } else if (p >= highTriggerPercent) {
    if (allowPowerUpTrigger) {
      oled.drawStr(0, 43, "STATUS: SURGE READY");
      oled.drawStr(0, 60, "PRESS # TO TRIGGER");
    } else {
      oled.drawStr(0, 43, "STATUS: DANGER HIGH");
      oled.drawStr(0, 60, "LOWER POWER NOW");
    }
  } else {
    oled.drawStr(0, 43, "STATUS: UNSTABLE");
    oled.drawStr(0, 60, "TURN DIAL");
  }
}

void drawOledShutdown() {
  unsigned long elapsed = millis() - shutdownStartedAt;
  int progress = map(elapsed, 0, SHUTDOWN_DURATION_MS, 0, 100);
  if (progress < 0) progress = 0;
  if (progress > 100) progress = 100;

  oled.setFont(u8g2_font_6x12_tf);

  int frame = shutdownFrame % 8;

  if (frame == 0) {
    oled.drawStr(0, 12, "> shutdown -h now");
    oled.drawStr(0, 28, "override accepted");
    oled.drawStr(0, 44, "stopping services...");
    oled.drawStr(0, 60, "do not remove key");
  } else if (frame == 1) {
    oled.drawStr(0, 12, "core.bus........OK");
    oled.drawStr(0, 28, "relay.lock......OK");
    oled.drawStr(0, 44, "timer.daemon....STOP");
    oled.drawStr(0, 60, "signal closing...");
  } else if (frame == 2) {
    oled.drawStr(0, 12, "SYS_ERR 0x19");
    oled.drawStr(0, 28, "PWR_DROP_DETECTED");
    oled.drawStr(0, 44, "//// SIGNAL ////");
    oled.drawStr(0, 60, "//// LOST //////");
  } else if (frame == 3) {
    oled.drawStr(0, 12, "KERNEL PANIC");
    oled.drawStr(0, 28, "RECOVERY MODE");
    oled.drawStr(0, 44, "SAFE SHUTDOWN");
    oled.drawStr(0, 60, "WATCHDOG HALT");
  } else if (frame == 4) {
    oled.drawStr(0, 12, "#### SYS NOISE ####");
    oled.drawStr(0, 28, "A/O/J/CASE/01");
    oled.drawStr(0, 44, "CORE OUTPUT LOW");
    oled.drawStr(0, 60, "KEEP DIAL DOWN");
  } else if (frame == 5) {
    oled.drawStr(0, 12, "PWR_BUS: //////");
    oled.drawStr(0, 28, "AUTH: OK");
    oled.drawStr(0, 44, "RELAY: OFFLINE");
    oled.drawStr(0, 60, "TIMER: STOPPING");
  } else if (frame == 6) {
    oled.drawStr(0, 12, "SHUTDOWN");
    oled.drawStr(0, 28, "[########----]");
    oled.drawStr(0, 44, "DO NOT REMOVE KEY");
    String line = "PROGRESS: " + String(progress) + "%";
    oled.drawStr(0, 60, line.c_str());
  } else {
    oled.drawStr(0, 12, "AOJ BLACKBOX");
    oled.drawStr(0, 28, "SYSTEM HALTING");
    oled.drawStr(0, 44, "SAFE MODE ACTIVE");
    String line = "PROGRESS: " + String(progress) + "%";
    oled.drawStr(0, 60, line.c_str());
  }
}

void drawOledDisarmed() {
  oled.setFont(u8g2_font_9x15B_tf);
  oled.drawStr(12, 28, "SYSTEM SAFE");
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 48, "DISARMED BY POWER");
  oled.drawStr(0, 62, "REPORT TO ADMIN");
}

void drawOledTriggered() {
  oled.setFont(u8g2_font_9x15B_tf);
  oled.drawStr(10, 28, "FAILSAFE");
  oled.drawStr(16, 46, "TRIGGERED");
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 62, "SIGNAL SENT TO ADMIN");
}

void updateLcd() {
  int p = readPowerPercent();

  if (state == STATE_SAFE) {
    lcdPrintLine(0, "AOJ OVERRIDE CASE");
    lcdPrintLine(1, "STATE: SAFE");
    lcdPrintLine(2, "FLIP SWITCH TO ARM");
    lcdPrintLine(3, "IP: 192.168.4.1");
    return;
  }

  if (state == STATE_ARMING_CODE) {
    lcdPrintLine(0, "STAFF ARMING MODE");
    lcdPrintLine(1, "ENTER ARM CODE");
    lcdPrintLine(2, "CODE: " + maskedInput());
    lcdPrintLine(3, "# OK   * CLEAR");
    return;
  }

  if (state == STATE_ARMED_NEED_USB) {
    lcdPrintLine(0, "SYSTEM ARMED");
    lcdPrintLine(1, "TIME: " + formatTime(remainingSeconds));
    lcdPrintLine(2, "OVERRIDE KEY REQ");
    lcdPrintLine(3, "FIND USB KEY");
    return;
  }

  if (state == STATE_WAIT_SECURITY_CODE) {
    lcdPrintLine(0, "OVERRIDE ACTIVE");
    lcdPrintLine(1, "TIME: " + formatTime(remainingSeconds));
    lcdPrintLine(2, "ENTER SEC CODE");
    lcdPrintLine(3, "CODE: " + maskedInput());
    return;
  }

  if (state == STATE_POWER_CONTROL) {
    lcdPrintLine(0, "POWER CONTROL");
    lcdPrintLine(1, "TIME: " + formatTime(remainingSeconds) + " PWR:" + String(p) + "%");

    if (p <= lowDisarmPercent) {
      lcdPrintLine(2, "POWER DOWN READY");
      lcdPrintLine(3, "PRESS # TO DISARM");
    } else if (p >= highTriggerPercent) {
      if (allowPowerUpTrigger) {
        lcdPrintLine(2, "POWER UP READY");
        lcdPrintLine(3, "PRESS # TO TRIGGER");
      } else {
        lcdPrintLine(2, "POWER TOO HIGH");
        lcdPrintLine(3, "TURN DIAL DOWN");
      }
    } else {
      lcdPrintLine(2, "STATUS: UNSTABLE");
      lcdPrintLine(3, "LOW=SAFE HIGH=FAIL");
    }
    return;
  }

  if (state == STATE_SHUTDOWN_SEQUENCE) {
    unsigned long elapsed = millis() - shutdownStartedAt;
    int progress = map(elapsed, 0, SHUTDOWN_DURATION_MS, 0, 100);
    if (progress < 0) progress = 0;
    if (progress > 100) progress = 100;

    lcdPrintLine(0, "POWER DOWN STARTED");
    lcdPrintLine(1, "DO NOT REMOVE KEY");
    lcdPrintLine(2, "CORE OUTPUT: " + String(p) + "%");
    lcdPrintLine(3, "SHUTDOWN: " + String(progress) + "%");
    return;
  }

  if (state == STATE_DISARMED) {
    lcdPrintLine(0, "AOJ OVERRIDE CASE");
    lcdPrintLine(1, "SYSTEM SAFE");
    lcdPrintLine(2, "DISARMED BY POWER");
    lcdPrintLine(3, "REPORT TO ADMIN");
    return;
  }

  if (state == STATE_TRIGGERED) {
    lcdPrintLine(0, "AOJ OVERRIDE CASE");
    lcdPrintLine(1, "FAILSAFE TRIGGERED");
    lcdPrintLine(2, "ADMIN SIGNAL SENT");
    lcdPrintLine(3, "HORN ACTIVE");
    return;
  }
}

void updateDisplays() {
  if (millis() - lastDisplayUpdate < 150) return;
  lastDisplayUpdate = millis();

  updateLcd();

  oled.clearBuffer();

  if (state == STATE_SAFE) drawOledSafe();
  else if (state == STATE_ARMING_CODE) drawOledArming();
  else if (state == STATE_ARMED_NEED_USB) drawOledNeedUsb();
  else if (state == STATE_WAIT_SECURITY_CODE) drawOledSecurity();
  else if (state == STATE_POWER_CONTROL) drawOledPowerControl();
  else if (state == STATE_SHUTDOWN_SEQUENCE) drawOledShutdown();
  else if (state == STATE_DISARMED) drawOledDisarmed();
  else if (state == STATE_TRIGGERED) drawOledTriggered();

  oled.sendBuffer();
}

// =====================================================
// WIFI CONTROL PANEL
// =====================================================

// Web control panel removed - use LoRa commands or AOJ server interface
/*
String htmlPage() {
  String page = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AOJ Override Case</title>
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

<h1>AOJ Override Case</h1>

<div class="card">
  <h2>Status</h2>
  <div id="status" class="status">Loading...</div>
</div>

<div class="card">
  <h2>Setup</h2>

  <label>Arm Code</label>
  <input id="armCode" type="text" inputmode="numeric" maxlength="10">

  <label>Security Code</label>
  <input id="securityCode" type="text" inputmode="numeric" maxlength="10">

  <label>Timer Minutes</label>
  <input id="timer" type="number" min="1" max="60">

  <label>Low Disarm Zone %</label>
  <input id="low" type="number" min="1" max="40">

  <label>High Trigger Zone %</label>
  <input id="high" type="number" min="60" max="100">

  <label>Shutdown Abort Above %</label>
  <input id="abort" type="number" min="10" max="60">

  <label>Max Mistakes</label>
  <input id="mistakes" type="number" min="1" max="10">

  <label>Power Up Trigger Allowed</label>
  <select id="allowTrig">
    <option value="1">Yes - high power triggers horn</option>
    <option value="0">No - high power counts as mistake</option>
  </select>

  <label>MP3 Volume 0-30</label>
  <input id="volume" type="number" min="0" max="30">

  <button class="blue" onclick="saveSettings()">Save Settings</button>
  <div class="small">Settings are saved to device memory.</div>
</div>

<div class="card">
  <h2>Game Control</h2>
  <button class="red" onclick="cmd('/api/arm')">MANUAL ARM</button>
  <button class="green" onclick="cmd('/api/disarm')">MANUAL DISARM</button>
  <button class="grey" onclick="cmd('/api/reset')">RESET TO SAFE</button>
  <button class="red" onclick="confirmTrigger()">MANUAL TRIGGER / HORN</button>
</div>

<div class="card">
  <h2>System Tests</h2>
  <div class="row">
    <button class="yellow" onclick="cmd('/api/test/buzzer')">Buzzer</button>
    <button class="yellow" onclick="cmd('/api/test/leds')">LEDs</button>
  </div>
  <button class="yellow" onclick="cmd('/api/test/relay')">Relay / Horn 1s</button>
  <button class="yellow" onclick="cmd('/api/test/mp3')">MP3 Test</button>
</div>

<script>
async function cmd(url) {
  await fetch(url);
  await refreshStatus();
}

async function saveSettings() {
  const params = new URLSearchParams();
  params.append('arm', document.getElementById('armCode').value);
  params.append('sec', document.getElementById('securityCode').value);
  params.append('timer', document.getElementById('timer').value);
  params.append('low', document.getElementById('low').value);
  params.append('high', document.getElementById('high').value);
  params.append('abort', document.getElementById('abort').value);
  params.append('mistakes', document.getElementById('mistakes').value);
  params.append('allowTrig', document.getElementById('allowTrig').value);
  params.append('volume', document.getElementById('volume').value);

  await fetch('/api/save?' + params.toString());
  await refreshStatus();
}

async function confirmTrigger() {
  if (confirm("Activate horn and send DETONATED signal?")) {
    await cmd('/api/trigger');
  }
}

async function refreshStatus() {
  const res = await fetch('/api/status');
  const data = await res.json();

  document.getElementById('status').innerText =
    "State: " + data.state + "\n" +
    "Time: " + data.time + "\n" +
    "Power: " + data.power + "% / " + data.voltage + "V\n" +
    "USB Key: " + data.usb + "\n" +
    "Mistakes: " + data.mistakes + "\n" +
    "Timer Rate: x" + data.rate + "\n" +
    "Horn Active: " + data.horn + "\n" +
    "IP: 192.168.4.1";

  document.getElementById('armCode').value = data.armCode;
  document.getElementById('securityCode').value = data.securityCode;
  document.getElementById('timer').value = data.timerMinutes;
  document.getElementById('low').value = data.low;
  document.getElementById('high').value = data.high;
  document.getElementById('abort').value = data.abort;
  document.getElementById('mistakes').value = data.maxMistakes;
  document.getElementById('allowTrig').value = data.allowTrig ? "1" : "0";
  document.getElementById('volume').value = data.volume;
}

setInterval(refreshStatus, 1000);
refreshStatus();
</script>

</body>
</html>
)rawliteral";

  return page;
}
*/

/*
void handleRoot() {
  server.send(200, "text/html", htmlPage());
}


*/

void setupMp3() {
  mp3Serial.begin(9600, SERIAL_8N1, MP3_RX_PIN, MP3_TX_PIN);
  delay(500);

  if (mp3.begin(mp3Serial)) {
    mp3Ready = true;
    mp3.volume(mp3Volume);
    playMp3(1);
  } else {
    mp3Ready = false;
  }
}

// =====================================================
// SETUP
// =====================================================

void setupPins() {
  pinMode(BUTTON_NEXT_PIN, INPUT_PULLUP);
  pinMode(BUTTON_SELECT_PIN, INPUT_PULLUP);
  pinMode(ARM_SWITCH_PIN, INPUT_PULLUP);
  pinMode(USB_DETECT_PIN, INPUT_PULLUP);

  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  setRelay(false);
  buzzerOff();

  analogReadResolution(12);
}

void setupDisplays() {
  Wire.begin(I2C_SDA, I2C_SCL);

  oled.begin();
  oled.setContrast(180);

  lcd.init();
  lcd.backlight();

  lcdPrintLine(0, "AOJ OVERRIDE CASE");
  lcdPrintLine(1, "BOOTING...");
  lcdPrintLine(2, "Created by Nineteen");
  lcdPrintLine(3, "Please wait");

  oled.clearBuffer();
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, "AOJ OVERRIDE CASE");
  oled.drawStr(0, 28, "Created by Nineteen");
  oled.drawStr(0, 44, "Booting system...");
  oled.drawFrame(0, 54, 128, 8);

  for (int i = 0; i <= 124; i += 4) {
    oled.drawBox(2, 56, i, 4);
    oled.sendBuffer();
    delay(20);
  }
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
    lcdPrintLine(0, "LoRa FAILED");
    lcdPrintLine(1, "Check module pins");
    lcdPrintLine(2, "System halted");
    lcdPrintLine(3, "");

    while (true) {
      digitalWrite(LED_YELLOW, HIGH);
      delay(200);
      digitalWrite(LED_YELLOW, LOW);
      delay(200);
    }
  }

  radio.startReceive();
}

void setupMp3() {
  mp3Serial.begin(9600, SERIAL_8N1, MP3_RX_PIN, MP3_TX_PIN);
  delay(500);

  if (mp3.begin(mp3Serial)) {
    mp3Ready = true;
    mp3.volume(mp3Volume);
    playMp3(1);
  } else {
    mp3Ready = false;
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[AOJ] Briefcase Bomb — " DEVICE_ID);

  remainingSeconds = configuredStartSeconds;

  setupPins();
  setupDisplays();
  setupMp3();
  setupRadio();

  resetToSafe();
  sendStatus();

  Serial.println("[AOJ] Ready");
}

// =====================================================
// MAIN LOOP
// =====================================================

void loop() {
  // ── LoRa receive ────────────────────────────────────────────────────────
  if (lora.available()) {
    String raw = lora.read();
    if (raw.length() > 0) {
      AOJFrame f = aojParseFrame(raw);
      if (f.valid && (f.deviceId == DEVICE_ID || f.deviceId == "*")) {
        if (f.command == "ARM") {
          armUnit();
          sendFrame("ACK", "OK", f.messageId);
        }
        else if (f.command == "DISARM") {
          disarmUnit("COMMAND");
          sendFrame("ACK", "OK", f.messageId);
        }
        else if (f.command == "TRIGGER") {
          triggerHorn("COMMAND");
          sendFrame("ACK", "OK", f.messageId);
        }
        else if (f.command == "RESET") {
          resetToSafe();
          sendFrame("ACK", "OK", f.messageId);
        }
        else if (f.command == "STATUS_REQUEST") {
          sendFrame("ACK", "OK", f.messageId);
          sendStatus();
        }
        else {
          sendFrame("ACK", "UNKNOWN", f.messageId);
        }
      }
    }
  }

  // ── Input handling ──────────────────────────────────────────────────────
  handleArmSwitch();
  handleButtons();
  handleUsbKey();
  handleKeypad();

  // ── Timer and horn ────────────────────────────────────────────────────────
  updateTimer();
  updateBeeps();
  updateHorn();
  updateShutdownSequence();

  // ── Display and status ────────────────────────────────────────────────────
  updateLeds();
  updateDisplays();

  if (millis() - lastStatusSend >= 15000) {
    lastStatusSend = millis();
    sendStatus();
  }
}
