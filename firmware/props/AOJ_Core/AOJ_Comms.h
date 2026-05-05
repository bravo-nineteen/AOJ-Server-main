/**
 * AOJ_Comms.h
 * ─────────────────────────────────────────────────────────────────────────────
 * AOJ frame building, parsing, CRC, and message-ID generation.
 *
 * Frame format (matches backend LoRa protocol):
 *   AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
 *
 * All functions are inline so no separate .cpp is needed.
 * ─────────────────────────────────────────────────────────────────────────────
 */
#pragma once
#include <Arduino.h>

// ─────────────────────────────────────────────────────────────────────────────
// Parsed frame
// ─────────────────────────────────────────────────────────────────────────────

struct AOJFrame {
  String deviceId;
  String command;
  String value;
  String messageId;
  bool   valid;   // false if header, CRC, or field-count check failed
};

// ─────────────────────────────────────────────────────────────────────────────
// CRC — XOR over all bytes in the payload string (everything before |CRC)
// Result: 2-character uppercase hex, matching backend calculate_crc()
// ─────────────────────────────────────────────────────────────────────────────

inline String aojCalculateCrc(const String &payload) {
  uint8_t crc = 0;
  for (size_t i = 0; i < payload.length(); i++) {
    crc ^= (uint8_t)payload[i];
  }
  char buf[3];
  snprintf(buf, sizeof(buf), "%02X", crc);
  return String(buf);
}

// ─────────────────────────────────────────────────────────────────────────────
// Build a complete AOJ frame string ready to transmit
// ─────────────────────────────────────────────────────────────────────────────

inline String aojBuildFrame(const char *deviceId,
                             const String &command,
                             const String &value,
                             const String &messageId) {
  String payload = String("AOJ|") + deviceId + "|" + command + "|" + value + "|" + messageId;
  return payload + "|" + aojCalculateCrc(payload);
}

// ─────────────────────────────────────────────────────────────────────────────
// Generate a 10-character hex message ID (millis XOR esp_random)
// ─────────────────────────────────────────────────────────────────────────────

inline String aojGenerateMessageId() {
  uint32_t val = (uint32_t)millis() ^ (uint32_t)esp_random();
  char buf[11];
  snprintf(buf, sizeof(buf), "%010lX", (unsigned long)val);
  return String(buf);
}

// ─────────────────────────────────────────────────────────────────────────────
// Parse a raw received string into an AOJFrame struct.
// Sets frame.valid = false on any error so callers can bail early.
// ─────────────────────────────────────────────────────────────────────────────

inline AOJFrame aojParseFrame(const String &raw) {
  AOJFrame frame;
  frame.valid = false;

  // Split into up to 6 parts on '|'
  String parts[6];
  int partCount = 0;
  int start = 0;
  for (int i = 0; i <= (int)raw.length() && partCount < 6; i++) {
    if (i == (int)raw.length() || raw[i] == '|') {
      parts[partCount++] = raw.substring(start, i);
      start = i + 1;
    }
  }

  if (partCount < 6) return frame;              // too few fields

  const String &header    = parts[0];
  const String &rxCrc     = parts[5];

  if (header != "AOJ") return frame;            // wrong network

  // Verify CRC
  String payload = header + "|" + parts[1] + "|" + parts[2] + "|" + parts[3] + "|" + parts[4];
  if (rxCrc != aojCalculateCrc(payload)) return frame;  // corrupted

  frame.deviceId  = parts[1];
  frame.command   = parts[2];
  frame.value     = parts[3];
  frame.messageId = parts[4];
  frame.valid     = true;
  return frame;
}

// ─────────────────────────────────────────────────────────────────────────────
// Battery ADC helper — returns 0-100 percent
// ─────────────────────────────────────────────────────────────────────────────

inline int aojReadBattery(int adcPin, int fullMv, int emptyMv) {
  if (adcPin < 0) return 100;
  int raw = analogRead(adcPin);
  // Assumes a 1:1 voltage divider; multiply raw ADC to millivolts then scale.
  // Adjust the multiplier (×2 here) for your actual divider ratio.
  int mv  = (int)(((long)raw * 3300 / 4095) * 2);
  int pct = (int)(((long)(mv - emptyMv) * 100) / (fullMv - emptyMv));
  return constrain(pct, 0, 100);
}
