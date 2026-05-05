/**
 * AOJ_LoRa.h
 * ─────────────────────────────────────────────────────────────────────────────
 * Thin wrapper around RadioLib for AOJ prop communication.
 *
 * Supports:
 *   SX1262 — Heltec V3
 *   SX1276 — Heltec V2, generic ESP32 LoRa boards
 *
 * Usage in your sketch:
 *   AojLoRa lora;
 *   lora.begin();
 *   lora.send("AOJ|...");
 *   if (lora.available()) {
 *     String frame = lora.read();
 *   }
 *
 * Requires: RadioLib (install via Arduino Library Manager)
 * ─────────────────────────────────────────────────────────────────────────────
 */
#pragma once

#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include "AOJ_BoardConfig.h"

// ─────────────────────────────────────────────────────────────────────────────
// ISR flag — lives in IRAM for fast interrupt response
// ─────────────────────────────────────────────────────────────────────────────
static volatile bool _aojLoraFlag = false;

#if defined(AOJ_RADIO_SX1262)
static SX1262 _aojRadio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
static void IRAM_ATTR _aojLoraISR() { _aojLoraFlag = true; }

#elif defined(AOJ_RADIO_SX1276)
static SX1276 _aojRadio = new Module(LORA_NSS, LORA_DIO0, LORA_RST, LORA_DIO1);
static void IRAM_ATTR _aojLoraISR() { _aojLoraFlag = true; }

#else
  #error "AOJ_LoRa: No radio type defined. Check AOJ_BoardConfig.h."
#endif

// ─────────────────────────────────────────────────────────────────────────────
// AojLoRa class
// ─────────────────────────────────────────────────────────────────────────────

class AojLoRa {
public:
  // Call once in setup().
  // Returns true on success, false on hardware failure.
  bool begin() {
    // Override SPI pins if the board needs non-default wiring.
    SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

    int state = _aojRadio.begin(
      LORA_FREQUENCY,
      LORA_BANDWIDTH,
      LORA_SF,
      LORA_CR,
      LORA_SYNC_WORD,
      LORA_TX_POWER
    );

    if (state != RADIOLIB_ERR_NONE) {
      Serial.print("[LORA] Init failed: ");
      Serial.println(state);
      return false;
    }

#if defined(AOJ_RADIO_SX1262)
    _aojRadio.setDio1Action(_aojLoraISR);
#elif defined(AOJ_RADIO_SX1276)
    _aojRadio.setDio0Action(_aojLoraISR, RISING);
#endif

    _aojRadio.startReceive();
    Serial.println("[LORA] Ready");
    return true;
  }

  // Transmit a frame string. Automatically re-enters receive mode.
  bool send(const String &frame) {
    Serial.print("[LORA TX] "); Serial.println(frame);
    int state = _aojRadio.transmit(frame);
    _aojRadio.startReceive();   // always return to RX
    if (state != RADIOLIB_ERR_NONE) {
      Serial.print("[LORA TX] Error: "); Serial.println(state);
      return false;
    }
    return true;
  }

  // Returns true if a packet is waiting.
  bool available() { return _aojLoraFlag; }

  // Read and return the next received frame string.
  // Call only when available() returns true.
  String read() {
    _aojLoraFlag = false;
    String data;
    int state = _aojRadio.readData(data);
    _aojRadio.startReceive();
    if (state != RADIOLIB_ERR_NONE) {
      Serial.print("[LORA RX] Read error: "); Serial.println(state);
      return "";
    }
    Serial.print("[LORA RX] "); Serial.println(data);
    return data;
  }

  // Current RSSI of last received packet (dBm as integer 0-100 scaled).
  // Returns raw dBm — you can scale it yourself for status reports.
  int rssiRaw() { return (int)_aojRadio.getRSSI(); }

  // Convenience: return RSSI as 0–100 percent (assuming -30 = 100%, -120 = 0%)
  int rssiPercent() {
    int dbm = (int)_aojRadio.getRSSI();
    int pct = (int)(((long)(dbm + 120) * 100) / 90);
    return constrain(pct, 0, 100);
  }
};
