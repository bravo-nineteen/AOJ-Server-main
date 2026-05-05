/**
 * AOJ_BoardConfig.h
 * ─────────────────────────────────────────────────────────────────────────────
 * Pin and radio-type definitions for supported boards.
 *
 * SELECT YOUR BOARD by defining ONE of the following BEFORE including this
 * header (either at the top of your .ino or in Arduino IDE board options):
 *
 *   #define BOARD_HELTEC_V2       // Heltec WiFi LoRa 32 V2  — SX1276
 *   #define BOARD_HELTEC_V3       // Heltec WiFi LoRa 32 V3  — SX1262  (default if nothing set)
 *   #define BOARD_ESP32_GENERIC   // TTGO LoRa32 V2.1 / similar — SX1276
 *
 * You can override any individual pin or frequency by #define-ing it BEFORE
 * including AOJ_Core.h.
 * ─────────────────────────────────────────────────────────────────────────────
 */
#pragma once

// ── Default board if nothing is specified ────────────────────────────────────
#if !defined(BOARD_HELTEC_V2) && !defined(BOARD_HELTEC_V3) && !defined(BOARD_ESP32_GENERIC)
  #define BOARD_HELTEC_V3
#endif

// ═════════════════════════════════════════════════════════════════════════════
// Heltec WiFi LoRa 32 V2  (SX1276)
// ═════════════════════════════════════════════════════════════════════════════
#if defined(BOARD_HELTEC_V2)

  #define AOJ_RADIO_SX1276        // tells AOJ_LoRa.h which class to use

  #ifndef LORA_NSS
    #define LORA_NSS   18
  #endif
  #ifndef LORA_DIO0               // SX1276: DIO0 = RxDone / TxDone
    #define LORA_DIO0  26
  #endif
  #ifndef LORA_RST
    #define LORA_RST   14
  #endif
  #ifndef LORA_DIO1               // used as second DIO (optional)
    #define LORA_DIO1  35
  #endif
  // SX1276 has no BUSY pin
  #define LORA_HAS_BUSY 0

  // SPI (VSPI)
  #ifndef LORA_SCK
    #define LORA_SCK   5
  #endif
  #ifndef LORA_MISO
    #define LORA_MISO  19
  #endif
  #ifndef LORA_MOSI
    #define LORA_MOSI  27
  #endif

  // Board peripherals
  #define BOARD_HAS_OLED 1
  #define OLED_SDA       4
  #define OLED_SCL       15
  #define OLED_RST       16
  #define BOARD_LED_PIN  25       // onboard LED (active HIGH)

// ═════════════════════════════════════════════════════════════════════════════
// Heltec WiFi LoRa 32 V3  (SX1262)
// ═════════════════════════════════════════════════════════════════════════════
#elif defined(BOARD_HELTEC_V3)

  #define AOJ_RADIO_SX1262

  #ifndef LORA_NSS
    #define LORA_NSS   8
  #endif
  #ifndef LORA_DIO1               // SX1262: DIO1 = IRQ
    #define LORA_DIO1  14
  #endif
  #ifndef LORA_RST
    #define LORA_RST   12
  #endif
  #ifndef LORA_BUSY
    #define LORA_BUSY  13
  #endif
  #define LORA_HAS_BUSY 1

  // SPI (FSPI on V3)
  #ifndef LORA_SCK
    #define LORA_SCK   9
  #endif
  #ifndef LORA_MISO
    #define LORA_MISO  11
  #endif
  #ifndef LORA_MOSI
    #define LORA_MOSI  10
  #endif

  #define BOARD_HAS_OLED 1
  #define OLED_SDA       17
  #define OLED_SCL       18
  #define OLED_RST       21
  #define BOARD_LED_PIN  35       // Vext control; HIGH = external 3.3V on

// ═════════════════════════════════════════════════════════════════════════════
// Generic ESP32 + SX1276  (e.g. TTGO LoRa32 V2.1, LilyGO similar)
// ═════════════════════════════════════════════════════════════════════════════
#elif defined(BOARD_ESP32_GENERIC)

  #define AOJ_RADIO_SX1276

  #ifndef LORA_NSS
    #define LORA_NSS   18
  #endif
  #ifndef LORA_DIO0
    #define LORA_DIO0  26
  #endif
  #ifndef LORA_RST
    #define LORA_RST   23
  #endif
  #ifndef LORA_DIO1
    #define LORA_DIO1  33
  #endif
  #define LORA_HAS_BUSY 0

  #ifndef LORA_SCK
    #define LORA_SCK   5
  #endif
  #ifndef LORA_MISO
    #define LORA_MISO  19
  #endif
  #ifndef LORA_MOSI
    #define LORA_MOSI  27
  #endif

  #define BOARD_HAS_OLED 0
  #define BOARD_LED_PIN  25

#endif // board selection

// ─────────────────────────────────────────────────────────────────────────────
// LoRa RF parameters — shared defaults (override before including AOJ_Core.h)
// ─────────────────────────────────────────────────────────────────────────────

#ifndef LORA_FREQUENCY
  #define LORA_FREQUENCY   923.0   // MHz — Japan 920 MHz ISM band
#endif
#ifndef LORA_BANDWIDTH
  #define LORA_BANDWIDTH   125.0   // kHz
#endif
#ifndef LORA_SF
  #define LORA_SF          9       // Spreading Factor 7–12
#endif
#ifndef LORA_CR
  #define LORA_CR          7       // Coding rate (5=4/5 … 8=4/8)
#endif
#ifndef LORA_SYNC_WORD
  #define LORA_SYNC_WORD   0x34    // AOJ private network sync word
#endif
#ifndef LORA_TX_POWER
  #define LORA_TX_POWER    17      // dBm — stay within regional limits
#endif

// ─────────────────────────────────────────────────────────────────────────────
// Battery ADC  (set BATTERY_ADC_PIN to -1 if no battery monitor fitted)
// ─────────────────────────────────────────────────────────────────────────────
#ifndef BATTERY_ADC_PIN
  #define BATTERY_ADC_PIN  35
#endif
#ifndef BATTERY_FULL_MV
  #define BATTERY_FULL_MV  4200
#endif
#ifndef BATTERY_EMPTY_MV
  #define BATTERY_EMPTY_MV 3300
#endif
