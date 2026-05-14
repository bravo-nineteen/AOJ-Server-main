#!/usr/bin/env python3
"""Example runner for Heltec V3 USB LoRa gateway.

Usage:
  python examples/lora_gateway_test.py
  python examples/lora_gateway_test.py --port /dev/ttyACM0
  python examples/lora_gateway_test.py --message "HELLO FIELD"
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

# Allow running from repository root without package installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lora_gateway import HeltecLoRaGateway  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Heltec V3 LoRa gateway test")
    parser.add_argument("--port", help="Manual serial port override (example: /dev/ttyACM0)")
    parser.add_argument(
        "--message",
        default=f"AOJ gateway test @ {int(time.time())}",
        help="Test LoRa payload to transmit",
    )
    args = parser.parse_args()

    gateway = HeltecLoRaGateway()

    if not gateway.connect(port=args.port):
        print("[TEST] Connect failed")
        return 1

    if not gateway.ping():
        print("[TEST] Ping failed")
        return 1

    current_status = gateway.status()
    print(f"[TEST] Status: {current_status}")

    if not gateway.send_message(args.message):
        print("[TEST] Send failed")
        return 1

    print("[TEST] Listening for RX messages. Press Ctrl+C to stop.")

    running = True

    def _stop(_sig, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while running:
            for payload in gateway.read_messages():
                print(f"[RX] {payload}")
            time.sleep(0.1)
    finally:
        gateway.disconnect()

    print("[TEST] Exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
