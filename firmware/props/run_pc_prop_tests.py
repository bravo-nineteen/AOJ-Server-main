#!/usr/bin/env python3
"""Run desktop simulation tests for CP_Unit and GM_Unit."""

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parent


def main() -> None:
    cp_test = ROOT / "CP_Unit" / "test_harness.py"
    gm_test = ROOT / "GM_Unit" / "test_harness.py"

    print("Running CP_Unit simulation...")
    runpy.run_path(str(cp_test), run_name="__main__")

    print("Running GM_Unit simulation...")
    runpy.run_path(str(gm_test), run_name="__main__")

    print("All prop PC simulations passed")


if __name__ == "__main__":
    main()
