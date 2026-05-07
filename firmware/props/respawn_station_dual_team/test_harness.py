#!/usr/bin/env python3
"""
test_harness.py

Desktop test harness for the dual-team respawn station logic.
Run: python test_harness.py

This simulates both RED and BLUE units and validates:
- Ready state transitions
- Countdown logic
- Game start flow
- Count increments and limit checks
- Peer packet handling
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

class Team(IntEnum):
    RED = 0
    BLUE = 1

class GameMode(IntEnum):
    RECORD_ONLY = 0
    KILL_LIMIT = 1
    RESPAWN_LIMIT = 2
    FLAG_CAPTURE = 3

class GameState(IntEnum):
    IDLE = 0
    READY = 1
    COUNTDOWN = 2
    RUNNING = 3
    GAMEOVER = 4

@dataclass
class Unit:
    device_id: str
    local_team: Team
    game_mode: GameMode = GameMode.RECORD_ONLY
    game_state: GameState = GameState.IDLE
    
    admin_enabled: bool = True
    red_ready: bool = False
    blue_ready: bool = False
    
    red_count: int = 0
    blue_count: int = 0
    
    limit_value: int = 20
    countdown_seconds: int = 10
    respawn_delay_seconds: int = 5
    
    last_message: str = "BOOT"
    game_over_reason: str = ""
    countdown_start_ms: int = 0
    
    def team_name(self) -> str:
        return "RED" if self.local_team == Team.RED else "BLUE"
    
    def game_state_name(self) -> str:
        names = {
            GameState.IDLE: "IDLE",
            GameState.READY: "READY",
            GameState.COUNTDOWN: "COUNTDOWN",
            GameState.RUNNING: "RUNNING",
            GameState.GAMEOVER: "GAME OVER",
        }
        return names.get(self.game_state, "UNKNOWN")
    
    def game_mode_name(self) -> str:
        names = {
            GameMode.RECORD_ONLY: "RECORD ONLY",
            GameMode.KILL_LIMIT: "KILL LIMIT",
            GameMode.RESPAWN_LIMIT: "RESPAWN LIMIT",
            GameMode.FLAG_CAPTURE: "FLAG CAPTURE",
        }
        return names.get(self.game_mode, "UNKNOWN")
    
    def mark_ready(self):
        if not self.admin_enabled or self.game_state == GameState.GAMEOVER:
            self.last_message = "READY_REJECTED"
            return
        
        if self.local_team == Team.RED:
            self.red_ready = True
        else:
            self.blue_ready = True
        
        self.game_state = GameState.READY
        self.last_message = f"{self.team_name()} READY"
    
    def handle_peer_ready(self, sender_team: Team):
        if sender_team == self.local_team:
            return
        
        if sender_team == Team.RED:
            self.red_ready = True
        else:
            self.blue_ready = True
        
        if self.red_ready and self.blue_ready:
            self.game_state = GameState.COUNTDOWN
            self.countdown_start_ms = 0
            self.last_message = "COUNTDOWN_START"
    
    def tick_countdown(self, elapsed_ms: int):
        if self.game_state != GameState.COUNTDOWN:
            return
        
        elapsed_seconds = elapsed_ms // 1000
        if elapsed_seconds >= self.countdown_seconds:
            self.game_state = GameState.RUNNING
            self.last_message = "GAME START"
    
    def register_action_press(self):
        if not self.admin_enabled or self.game_state != GameState.RUNNING:
            self.last_message = "ACTION_REJECTED"
            return
        
        if self.local_team == Team.RED:
            self.red_count += 1
            count = self.red_count
        else:
            self.blue_count += 1
            count = self.blue_count
        
        self.last_message = f"COUNT_{count}"
        
        # Check limits
        if self.game_mode == GameMode.KILL_LIMIT:
            if self.red_count >= self.limit_value:
                self.game_state = GameState.GAMEOVER
                self.game_over_reason = "RED HIT KILL LIMIT"
                self.last_message = "GAMEOVER"
            if self.blue_count >= self.limit_value:
                self.game_state = GameState.GAMEOVER
                self.game_over_reason = "BLUE HIT KILL LIMIT"
                self.last_message = "GAMEOVER"
    
    def handle_peer_count(self, value: str):
        if value.startswith("RED:"):
            self.red_count = int(value[4:])
        elif value.startswith("BLUE:"):
            self.blue_count = int(value[5:])
    
    def reset(self):
        self.red_ready = False
        self.blue_ready = False
        self.red_count = 0
        self.blue_count = 0
        self.game_over_reason = ""
        self.game_state = GameState.IDLE
        self.last_message = "RESET"
    
    def status(self):
        print(f"  [{self.device_id}] Team: {self.team_name()} | State: {self.game_state_name()} | Mode: {self.game_mode_name()} | Counts: R={self.red_count} B={self.blue_count} | Last: {self.last_message}")


def test_ready_state_transition():
    print("TEST 1: Ready State Transition")
    red = Unit("RESPAWN-RED-01", Team.RED)
    blue = Unit("RESPAWN-BLUE-01", Team.BLUE)
    
    red.status()
    blue.status()
    assert red.game_state == GameState.IDLE
    assert blue.game_state == GameState.IDLE
    
    red.mark_ready()
    print("  RED marked ready")
    red.status()
    assert red.game_state == GameState.READY
    assert red.red_ready == True
    
    blue.mark_ready()
    print("  BLUE marked ready")
    blue.status()
    assert blue.game_state == GameState.READY
    
    # Peer sync
    red.handle_peer_ready(Team.BLUE)
    blue.handle_peer_ready(Team.RED)
    print("  Peer sync complete")
    red.status()
    blue.status()
    assert red.game_state == GameState.COUNTDOWN
    assert blue.game_state == GameState.COUNTDOWN
    print("  ✓ PASS\n")


def test_countdown_and_game_start():
    print("TEST 2: Countdown and Game Start")
    red = Unit("RESPAWN-RED-01", Team.RED)
    blue = Unit("RESPAWN-BLUE-01", Team.BLUE)
    
    red.countdown_seconds = 3
    blue.countdown_seconds = 3
    red.game_state = GameState.COUNTDOWN
    blue.game_state = GameState.COUNTDOWN
    
    red.tick_countdown(0)
    blue.tick_countdown(0)
    assert red.game_state == GameState.COUNTDOWN
    
    red.tick_countdown(3500)  # Tick past 3 seconds
    blue.tick_countdown(3500)
    print("  After countdown expiry:")
    red.status()
    blue.status()
    assert red.game_state == GameState.RUNNING
    assert blue.game_state == GameState.RUNNING
    print("  ✓ PASS\n")


def test_action_presses_and_count_sync():
    print("TEST 3: Action Presses and Count Sync")
    red = Unit("RESPAWN-RED-01", Team.RED)
    blue = Unit("RESPAWN-BLUE-01", Team.BLUE)
    
    red.game_mode = GameMode.KILL_LIMIT
    blue.game_mode = GameMode.KILL_LIMIT
    red.limit_value = 5
    blue.limit_value = 5
    red.game_state = GameState.RUNNING
    blue.game_state = GameState.RUNNING
    
    for i in range(3):
        red.register_action_press()
        blue.handle_peer_count(f"RED:{red.red_count}")
    
    print("  RED pressed 3 times:")
    red.status()
    blue.status()
    assert red.red_count == 3
    assert blue.red_count == 3
    
    for i in range(5):
        blue.register_action_press()
        red.handle_peer_count(f"BLUE:{blue.blue_count}")
    
    print("  BLUE pressed 5 times (hit limit):")
    red.status()
    blue.status()
    assert blue.game_state == GameState.GAMEOVER
    assert "BLUE HIT KILL LIMIT" in blue.game_over_reason
    assert red.blue_count == 5
    print("  ✓ PASS\n")


def test_reset_and_restart():
    print("TEST 4: Reset and Restart")
    red = Unit("RESPAWN-RED-01", Team.RED)
    blue = Unit("RESPAWN-BLUE-01", Team.BLUE)
    
    red.game_state = GameState.GAMEOVER
    blue.game_state = GameState.GAMEOVER
    red.red_count = 10
    blue.blue_count = 10
    
    red.reset()
    blue.reset()
    print("  After reset:")
    red.status()
    blue.status()
    assert red.game_state == GameState.IDLE
    assert blue.game_state == GameState.IDLE
    assert red.red_count == 0
    assert blue.blue_count == 0
    print("  ✓ PASS\n")


def test_admin_disable():
    print("TEST 5: Admin Disable")
    red = Unit("RESPAWN-RED-01", Team.RED)
    
    red.admin_enabled = False
    red.mark_ready()
    print("  Attempted ready while disabled:")
    red.status()
    assert red.game_state == GameState.IDLE
    assert red.last_message == "READY_REJECTED"
    print("  ✓ PASS\n")


def test_record_only_mode():
    print("TEST 6: Record-Only Mode (No Limit)")
    red = Unit("RESPAWN-RED-01", Team.RED)
    blue = Unit("RESPAWN-BLUE-01", Team.BLUE)
    
    red.game_mode = GameMode.RECORD_ONLY
    blue.game_mode = GameMode.RECORD_ONLY
    red.limit_value = 5
    blue.limit_value = 5
    red.game_state = GameState.RUNNING
    blue.game_state = GameState.RUNNING
    
    for i in range(10):
        red.register_action_press()
        blue.handle_peer_count(f"RED:{red.red_count}")
    
    print("  RED pressed 10 times (exceeds limit but record-only):")
    red.status()
    blue.status()
    assert red.game_state == GameState.RUNNING  # Still running
    assert red.red_count == 10
    print("  ✓ PASS\n")


if __name__ == "__main__":
    print("=== AOJ Dual-Team Respawn Station Test Harness ===\n")
    
    try:
        test_ready_state_transition()
        test_countdown_and_game_start()
        test_action_presses_and_count_sync()
        test_reset_and_restart()
        test_admin_disable()
        test_record_only_mode()
        
        print("=== All Tests Passed ===")
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)
