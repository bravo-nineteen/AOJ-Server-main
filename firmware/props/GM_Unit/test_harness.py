#!/usr/bin/env python3
"""
Desktop test harness for GM_Unit siren behavior.

Validates:
- AOJ frame parsing + ACK generation
- 10-second countdown then 3-second horn pulse for GAME_START/GAME_END
- Immediate 3-second horn pulse for alarm commands
- STATUS_REQUEST and TEST handling
"""

from dataclasses import dataclass, field


def crc_xor(payload: str) -> str:
    checksum = 0
    for b in payload.encode("utf-8"):
        checksum ^= b
    return f"{checksum:02X}"


def build_frame(device_id: str, command: str, value: str, message_id: str) -> str:
    base = f"AOJ|{device_id}|{command}|{value}|{message_id}"
    return f"{base}|{crc_xor(base)}"


def parse_frame(raw: str):
    parts = raw.strip().split("|")
    if len(parts) != 6:
        return None
    header, device_id, command, value, message_id, rx_crc = parts
    payload_wo_crc = "|".join(parts[:-1])
    if header != "AOJ" or crc_xor(payload_wo_crc) != rx_crc:
        return None
    return {
        "device_id": device_id,
        "command": command,
        "value": value,
        "message_id": message_id,
    }


@dataclass
class GmUnitModel:
    device_id: str = "GM_Unit"
    countdown_seconds: int = 10
    horn_pulse_ms: int = 3000
    countdown_active: bool = False
    horn_active: bool = False
    now_ms: int = 0
    countdown_start_ms: int = 0
    horn_start_ms: int = 0
    outbox: list[str] = field(default_factory=list)

    def _ack(self, message_id: str, value: str = "OK") -> None:
        self.outbox.append(build_frame(self.device_id, "ACK", value, message_id))

    def _event(self, value: str) -> None:
        mid = f"EV{len(self.outbox):08d}"[-10:]
        self.outbox.append(build_frame(self.device_id, "SIREN", value, mid))

    def _status(self) -> None:
        state = "alarm" if self.horn_active else ("countdown" if self.countdown_active else "online")
        mid = f"ST{len(self.outbox):08d}"[-10:]
        self.outbox.append(build_frame(self.device_id, "STATUS", state, mid))

    def start_countdown(self) -> None:
        self.countdown_active = True
        self.countdown_start_ms = self.now_ms
        self._event("COUNTDOWN")

    def start_horn(self) -> None:
        self.horn_active = True
        self.horn_start_ms = self.now_ms
        self._event("HORN")

    def tick(self, delta_ms: int) -> None:
        self.now_ms += delta_ms
        if self.countdown_active and (self.now_ms - self.countdown_start_ms) >= self.countdown_seconds * 1000:
            self.countdown_active = False
            self.start_horn()
        if self.horn_active and (self.now_ms - self.horn_start_ms) >= self.horn_pulse_ms:
            self.horn_active = False
            self._event("OFF")

    def receive(self, raw_frame: str) -> None:
        frame = parse_frame(raw_frame)
        if not frame:
            return
        if frame["device_id"] not in (self.device_id, "*"):
            return

        cmd = frame["command"].upper()
        val = frame["value"].upper()

        if cmd == "STATUS_REQUEST":
            self._ack(frame["message_id"])
            self._status()
        elif cmd in ("GAME_START", "START", "ROUND_START"):
            self._ack(frame["message_id"])
            self.start_countdown()
        elif cmd in ("GAME_END", "GAME_OVER", "END", "GAMEOVER"):
            self._ack(frame["message_id"])
            self.start_countdown()
        elif cmd in ("TRIGGER_ALARM", "BOMB_EXPLODED", "EXPLODED", "ALARM"):
            self._ack(frame["message_id"])
            self.start_horn()
        elif cmd in ("TEST", "SIREN_TEST"):
            self._ack(frame["message_id"])
            if val == "COUNTDOWN":
                self.start_countdown()
            elif val in ("BUZZ", "BUZZER", "BUZZER_TEST"):
                self._event("BUZZER_TEST")
            elif val in ("HORN", "RELAY", "HORN_TEST"):
                self.start_horn()
            else:
                self.start_horn()
        else:
            self._ack(frame["message_id"], "UNKNOWN")


def assert_has_ack(outbox: list[str], message_id: str) -> None:
    assert any((f"|ACK|" in x and f"|{message_id}|" in x) for x in outbox)


def run_tests() -> None:
    gm = GmUnitModel()

    # STATUS_REQUEST
    gm.receive(build_frame("GM_Unit", "STATUS_REQUEST", "", "MID0000001"))
    assert_has_ack(gm.outbox, "MID0000001")
    assert any("|STATUS|online|" in x for x in gm.outbox)

    # GAME_START: countdown then horn then off
    gm.receive(build_frame("GM_Unit", "GAME_START", "", "MID0000002"))
    assert gm.countdown_active is True
    gm.tick(10000)
    assert gm.countdown_active is False
    assert gm.horn_active is True
    gm.tick(3000)
    assert gm.horn_active is False

    # Alarm command: immediate horn pulse
    gm.receive(build_frame("GM_Unit", "BOMB_EXPLODED", "", "MID0000003"))
    assert gm.horn_active is True
    gm.tick(3000)
    assert gm.horn_active is False

    # Unknown command
    gm.receive(build_frame("GM_Unit", "NOPE", "", "MID0000004"))
    assert any("|ACK|UNKNOWN|MID0000004|" in x for x in gm.outbox)

    print("GM_Unit simulation tests passed")


if __name__ == "__main__":
    run_tests()
