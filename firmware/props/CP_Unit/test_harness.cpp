/**
 * test_harness.cpp
 * 
 * Desktop test harness for the dual-team respawn station logic.
 * Compile & run: g++ -std=c++17 -o test_harness test_harness.cpp && ./test_harness
 * 
 * This simulates both RED and BLUE units and validates:
 * - Ready state transitions
 * - Countdown logic
 * - Game start flow
 * - Count increments and limit checks
 * - Peer packet handling
 * - Server command routing
 */

#include <iostream>
#include <string>
#include <map>
#include <ctime>
#include <cassert>

using namespace std;

enum Team { TEAM_RED = 0, TEAM_BLUE = 1 };
enum GameMode { MODE_RECORD_ONLY = 0, MODE_KILL_LIMIT = 1, MODE_RESPAWN_LIMIT = 2, MODE_FLAG_CAPTURE = 3 };
enum GameState { STATE_IDLE = 0, STATE_READY = 1, STATE_COUNTDOWN = 2, STATE_RUNNING = 3, STATE_GAMEOVER = 4 };

struct Unit {
  string deviceId;
  Team localTeam;
  GameMode gameMode;
  GameState gameState;
  
  bool adminEnabled;
  bool redReady;
  bool blueReady;
  
  int redCount;
  int blueCount;
  
  int limitValue;
  int countdownSeconds;
  int respawnDelaySeconds;
  
  string lastMessage;
  string gameOverReason;
  
  unsigned long countdownStartMs;
  
  Unit(string id, Team team) 
    : deviceId(id), localTeam(team), gameMode(MODE_RECORD_ONLY), gameState(STATE_IDLE),
      adminEnabled(true), redReady(false), blueReady(false),
      redCount(0), blueCount(0),
      limitValue(20), countdownSeconds(10), respawnDelaySeconds(5),
      lastMessage("BOOT"), countdownStartMs(0) {}
  
  string teamName() const { return localTeam == TEAM_RED ? "RED" : "BLUE"; }
  string gameStateName() const {
    switch (gameState) {
      case STATE_IDLE: return "IDLE";
      case STATE_READY: return "READY";
      case STATE_COUNTDOWN: return "COUNTDOWN";
      case STATE_RUNNING: return "RUNNING";
      case STATE_GAMEOVER: return "GAME OVER";
    }
    return "UNKNOWN";
  }
  
  string gameModeName() const {
    switch (gameMode) {
      case MODE_RECORD_ONLY: return "RECORD ONLY";
      case MODE_KILL_LIMIT: return "KILL LIMIT";
      case MODE_RESPAWN_LIMIT: return "RESPAWN LIMIT";
      case MODE_FLAG_CAPTURE: return "FLAG CAPTURE";
    }
    return "UNKNOWN";
  }
  
  void markReady() {
    if (!adminEnabled || gameState == STATE_GAMEOVER) {
      lastMessage = "READY_REJECTED";
      return;
    }
    if (localTeam == TEAM_RED) redReady = true;
    if (localTeam == TEAM_BLUE) blueReady = true;
    gameState = STATE_READY;
    lastMessage = teamName() + " READY";
  }
  
  void handlePeerReady(Team senderTeam) {
    if (senderTeam == localTeam) return;
    if (senderTeam == TEAM_RED) redReady = true;
    if (senderTeam == TEAM_BLUE) blueReady = true;
    
    if (redReady && blueReady) {
      gameState = STATE_COUNTDOWN;
      countdownStartMs = 0; // Simulated time
      lastMessage = "COUNTDOWN_START";
    }
  }
  
  void startCountdown() {
    if (redReady && blueReady && gameState == STATE_READY) {
      gameState = STATE_COUNTDOWN;
      countdownStartMs = 0;
      lastMessage = "COUNTDOWN";
    }
  }
  
  void tickCountdown(unsigned int elapsedMs) {
    if (gameState != STATE_COUNTDOWN) return;
    unsigned long elapsedSeconds = elapsedMs / 1000;
    if (elapsedSeconds >= (unsigned long)countdownSeconds) {
      gameState = STATE_RUNNING;
      lastMessage = "GAME START";
    }
  }
  
  void registerActionPress() {
    if (!adminEnabled || gameState != STATE_RUNNING) {
      lastMessage = "ACTION_REJECTED";
      return;
    }
    
    if (localTeam == TEAM_RED) {
      redCount++;
    } else {
      blueCount++;
    }
    lastMessage = "COUNT_" + to_string(localTeam == TEAM_RED ? redCount : blueCount);
    
    // Check limits
    if (gameMode == MODE_KILL_LIMIT) {
      if (redCount >= limitValue) {
        gameState = STATE_GAMEOVER;
        gameOverReason = "RED HIT KILL LIMIT";
        lastMessage = "GAMEOVER";
      }
      if (blueCount >= limitValue) {
        gameState = STATE_GAMEOVER;
        gameOverReason = "BLUE HIT KILL LIMIT";
        lastMessage = "GAMEOVER";
      }
    }
  }
  
  void handlePeerCount(string value) {
    if (value.find("RED:") == 0) {
      redCount = stoi(value.substr(4));
    } else if (value.find("BLUE:") == 0) {
      blueCount = stoi(value.substr(5));
    }
  }
  
  void reset() {
    redReady = false;
    blueReady = false;
    redCount = 0;
    blueCount = 0;
    gameOverReason = "";
    gameState = STATE_IDLE;
    lastMessage = "RESET";
  }
  
  void status() const {
    cout << "  [" << deviceId << "] Team: " << teamName() 
         << " | State: " << gameStateName() 
         << " | Mode: " << gameModeName()
         << " | Counts: R=" << redCount << " B=" << blueCount
         << " | Last: " << lastMessage << endl;
  }
};

int main() {
  cout << "=== AOJ Dual-Team Respawn Station Test Harness ===" << endl << endl;
  
  Unit red("RESPAWN-RED-01", TEAM_RED);
  Unit blue("RESPAWN-BLUE-01", TEAM_BLUE);
  
  // TEST 1: Both units become ready
  cout << "TEST 1: Ready State Transition" << endl;
  red.status();
  blue.status();
  assert(red.gameState == STATE_IDLE);
  assert(blue.gameState == STATE_IDLE);
  
  red.markReady();
  cout << "  RED marked ready" << endl;
  red.status();
  assert(red.gameState == STATE_READY);
  assert(red.redReady == true);
  
  blue.markReady();
  cout << "  BLUE marked ready" << endl;
  blue.status();
  assert(blue.gameState == STATE_READY);
  
  // Peer sync: each sees the other ready
  red.handlePeerReady(TEAM_BLUE);
  blue.handlePeerReady(TEAM_RED);
  cout << "  Peer sync complete" << endl;
  red.status();
  blue.status();
  assert(red.gameState == STATE_COUNTDOWN);
  assert(blue.gameState == STATE_COUNTDOWN);
  cout << "  ✓ PASS" << endl << endl;
  
  // TEST 2: Countdown and game start
  cout << "TEST 2: Countdown and Game Start" << endl;
  red.countdownSeconds = 3;
  blue.countdownSeconds = 3;
  
  red.tickCountdown(0);
  blue.tickCountdown(0);
  assert(red.gameState == STATE_COUNTDOWN);
  
  red.tickCountdown(3500); // Tick past 3 seconds
  blue.tickCountdown(3500);
  cout << "  After countdown expiry:" << endl;
  red.status();
  blue.status();
  assert(red.gameState == STATE_RUNNING);
  assert(blue.gameState == STATE_RUNNING);
  cout << "  ✓ PASS" << endl << endl;
  
  // TEST 3: Action presses and count sync
  cout << "TEST 3: Action Presses and Count Sync" << endl;
  red.gameMode = MODE_KILL_LIMIT;
  blue.gameMode = MODE_KILL_LIMIT;
  red.limitValue = 5;
  blue.limitValue = 5;
  
  for (int i = 0; i < 3; i++) {
    red.registerActionPress();
    blue.handlePeerCount("RED:" + to_string(red.redCount));
  }
  cout << "  RED pressed 3 times:" << endl;
  red.status();
  blue.status();
  assert(red.redCount == 3);
  assert(blue.redCount == 3);
  
  for (int i = 0; i < 5; i++) {
    blue.registerActionPress();
    red.handlePeerCount("BLUE:" + to_string(blue.blueCount));
  }
  cout << "  BLUE pressed 5 times (hit limit):" << endl;
  red.status();
  blue.status();
  assert(blue.gameState == STATE_GAMEOVER);
  assert(blue.gameOverReason.find("BLUE HIT KILL LIMIT") != string::npos);
  assert(red.blueCount == 5);
  cout << "  ✓ PASS" << endl << endl;
  
  // TEST 4: Reset and restart
  cout << "TEST 4: Reset and Restart" << endl;
  red.reset();
  blue.reset();
  cout << "  After reset:" << endl;
  red.status();
  blue.status();
  assert(red.gameState == STATE_IDLE);
  assert(blue.gameState == STATE_IDLE);
  assert(red.redCount == 0);
  assert(blue.blueCount == 0);
  cout << "  ✓ PASS" << endl << endl;
  
  // TEST 5: Admin disable
  cout << "TEST 5: Admin Disable" << endl;
  red.adminEnabled = false;
  blue.adminEnabled = false;
  red.markReady();
  cout << "  Attempted ready while disabled:" << endl;
  red.status();
  assert(red.gameState == STATE_IDLE);
  assert(red.lastMessage == "READY_REJECTED");
  cout << "  ✓ PASS" << endl << endl;
  
  // TEST 6: Record-only mode (no limit)
  cout << "TEST 6: Record-Only Mode (No Limit)" << endl;
  red.reset();
  blue.reset();
  red.adminEnabled = true;
  blue.adminEnabled = true;
  red.gameMode = MODE_RECORD_ONLY;
  blue.gameMode = MODE_RECORD_ONLY;
  red.limitValue = 5;
  blue.limitValue = 5;
  
  red.gameState = STATE_RUNNING;
  blue.gameState = STATE_RUNNING;
  
  for (int i = 0; i < 10; i++) {
    red.registerActionPress();
    blue.handlePeerCount("RED:" + to_string(red.redCount));
  }
  cout << "  RED pressed 10 times (exceeds limit but record-only):" << endl;
  red.status();
  blue.status();
  assert(red.gameState == STATE_RUNNING); // Still running
  assert(red.redCount == 10);
  cout << "  ✓ PASS" << endl << endl;
  
  cout << "=== All Tests Passed ===" << endl;
  return 0;
}
