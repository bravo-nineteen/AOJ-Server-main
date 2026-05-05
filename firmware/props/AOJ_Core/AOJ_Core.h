/**
 * AOJ_Core.h
 * ─────────────────────────────────────────────────────────────────────────────
 * Umbrella header — include this one file in your sketch.
 *
 *   #include <AOJ_Core.h>
 *
 * It pulls in:
 *   AOJ_BoardConfig.h — pin defs for Heltec V2/V3 and generic ESP32
 *   AOJ_Comms.h       — frame building, parsing, CRC, message IDs, battery ADC
 *   AOJ_LoRa.h        — AojLoRa class (RadioLib wrapper)
 *   AOJ_WiFi.h        — AojWiFi class (optional HTTP status reporting)
 * ─────────────────────────────────────────────────────────────────────────────
 */
#pragma once

#include "AOJ_BoardConfig.h"
#include "AOJ_Comms.h"
#include "AOJ_LoRa.h"
#include "AOJ_WiFi.h"
