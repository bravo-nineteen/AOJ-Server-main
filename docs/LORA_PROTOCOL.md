# AOJ Command OS LoRa Protocol

## Status

The current LoRa implementation is a service skeleton in `backend/services/lora_service.py`.

What exists now:
- Command queue
- Message ID generation
- XOR CRC generation
- Pending ACK tracking
- Retry and timeout handling
- Mock transport mode for development

What does not exist yet:
- Real SX1262 or similar radio driver integration
- Radio configuration management
- Persistent prop telemetry history
- Encryption or authenticated command signing

This document describes the current message contract so firmware and backend work can stay aligned.

## Intended Use

The protocol is designed for low-bandwidth field prop traffic between the Raspberry Pi and remote devices such as:
- Bomb props
- Domination points
- Respawn stations
- Alarms
- Sensors

## Frame Format

Current message frame:

```text
AOJ|DEVICE_ID|COMMAND|VALUE|MESSAGE_ID|CRC
```

Field meanings:
- `AOJ`: constant frame header
- `DEVICE_ID`: unique prop identifier
- `COMMAND`: action or message type
- `VALUE`: command parameter or ACK value
- `MESSAGE_ID`: unique ID for ACK tracking
- `CRC`: simple XOR checksum in uppercase hexadecimal

Example command:

```text
AOJ|PROP-ALPHA|ARM|RED|A1B2C3D4E5|5F
```

Example acknowledgement:

```text
AOJ|PROP-ALPHA|ACK|OK|A1B2C3D4E5|33
```

## Header

The header is always `AOJ`.

Receivers should reject frames with a different header.

## Device IDs

Each prop should have a stable `DEVICE_ID` that matches the record stored in the Prop Network module.

Recommended style:
- `PROP-ALPHA`
- `BOMB-01`
- `DOM-RED-02`

Requirements:
- Unique per prop
- Stable across restarts
- Printed on the device housing if possible

## Message IDs

The backend currently generates a 10-character uppercase hex-like ID derived from a UUID.

Purpose:
- Match acknowledgements to pending commands
- Detect timeout and retry state

Firmware should return the same `MESSAGE_ID` in the ACK frame.

## CRC

Current CRC method:
- XOR each byte of the UTF-8 payload before the CRC field
- Format the result as two uppercase hexadecimal characters

Example calculation scope:

```text
AOJ|PROP-ALPHA|ARM|RED|A1B2C3D4E5
```

The CRC is calculated over that exact string, then appended as the final field.

Current limitations:
- This is only an integrity check
- It is not strong protection against collisions or malicious traffic

Future improvement options:
- CRC-16
- keyed message authentication
- signed command manifests for critical actions

## ACK Behavior

Expected ACK shape:

```text
AOJ|DEVICE_ID|ACK|VALUE|MESSAGE_ID|CRC
```

Expected ACK value examples:
- `OK`
- `BUSY`
- `REJECTED`
- `ERROR`

Current backend behavior:
- Valid ACK clears pending retry state for that message ID
- Device status is updated to `acknowledged`
- `last_seen`, `last_ack_at`, and `ack_value` are recorded in memory

## Retry and Timeout Logic

Current defaults:
- ACK timeout: 3 seconds
- Max retries: 3

Behavior:
1. Backend queues a command.
2. Command is transmitted and added to the pending ACK table.
3. If no ACK arrives before timeout, the backend retries.
4. After max retries, device state becomes `ack_timeout`.

This logic currently lives in memory only.

## Current Mock Mode

The service starts in `mock_mode=True`.

What mock mode does:
- Loops the outgoing frame into an internal incoming queue
- Generates a synthetic ACK frame with value `OK`

Why it exists:
- Lets frontend and backend development continue before hardware integration is ready
- Supports operator workflow validation on desktop and Windows hosts

## Suggested Command Vocabulary

The current codebase already uses prop commands such as:
- `arm`
- `disarm`
- `reset`
- `trigger_alarm`
- `STATUS_REQUEST`

Recommended firmware-side normalized radio commands:
- `ARM`
- `DISARM`
- `RESET`
- `ALARM`
- `STATUS_REQUEST`
- `STATUS_RESPONSE`
- `HEARTBEAT`

Use uppercase on the wire even if UI labels are lower-case.

## Suggested STATUS_RESPONSE Payload

The current backend does not yet parse structured status messages, but firmware should plan for compact payloads.

Example idea:

```text
AOJ|PROP-ALPHA|STATUS_RESPONSE|BAT=87,SIG=71,STATE=ARMED,FW=1.0.0|9ABCDE1234|7A
```

If you implement this later, document strict field ordering or switch to a tagged mini-format that the backend can parse consistently.

## Firmware Recommendations

- Validate header and CRC before acting on any command
- Ignore frames for other device IDs unless implementing a broadcast mode intentionally
- Return ACK quickly, even if the physical action takes longer
- Separate command receipt from actuator completion if hardware actions are slow
- Keep the device state machine explicit: idle, armed, triggered, fault, low_battery
- Include a watchdog or reset path for field recovery

## Security Notes

Current protocol security is minimal.

Treat the present skeleton as a development and local field prototype, not a hardened radio control system.

Before production hardware rollout, add:
- stronger integrity protection
- replay protection
- device authentication
- command authorization rules

## Integration Notes for Backend Developers

Current backend integration points:
- `send_command(device_id, command, value)`
- `request_device_status(device_id)`
- `broadcast_message(command, value)`
- `handle_ack(raw_message)`

Planned work:
- Replace mock transport in `_transmit()` with real radio send
- Feed incoming radio frames into `handle_ack()` or a future status parser
- Emit websocket and log events on failures and telemetry updates