# Team Terminals ↔ AOJ Server Integration Guide

## Overview

**Team Terminals** is a Flutter-based tablet/laptop application that provides a real-time command & control interface for team operations during Airsoft events. It connects to the **AOJ Command OS backend server** to manage rosters, game sessions, scoring, and communications.

## Architecture

### Network Model

```
┌─────────────────────────────────────────┐
│                                         │
│  Team Terminals (Tablet/Laptop)        │
│  ├─ Roster Management                   │
│  ├─ Game Session Control                │
│  ├─ Respawn Tracking                    │
│  ├─ Field Map & Comms Log              │
│  └─ Real-time Updates                   │
│                                         │
└──────────────────┬──────────────────────┘
                   │
            HTTP REST API
         (WiFi / LAN / WAN)
                   │
┌──────────────────▼──────────────────────┐
│                                         │
│   AOJ Command OS Backend Server         │
│   ├─ Player Management                  │
│   ├─ Game Session Orchestration         │
│   ├─ Event Logging & Scoring            │
│   ├─ System State Management            │
│   └─ WebSocket for Real-time Updates    │
│                                         │
└─────────────────────────────────────────┘
```

## Connection Flow

### 1. Initial Setup

```
Team Terminals Start
    ↓
[Check Network Configuration]
    ├─ Load server URL from preferences
    ├─ Or prompt user for server address
    └─ Test connection to /api/health
    ↓
[Authenticate/Register]
    ├─ POST /api/players (register terminal as operator)
    └─ Store session token (if enabled)
    ↓
[Load Initial Data]
    ├─ GET /api/players (team roster)
    ├─ GET /api/game-modes (available modes)
    └─ GET /api/game-sessions (active sessions)
    ↓
[Enter Game Lobby/Control Interface]
```

### 2. During Active Game Session

```
Game In Progress
    ↓
[Real-time Sync Loop]
    ├─ Poll /api/game-sessions/{id} (respawn counts, status)
    ├─ POST /api/game-sessions/{id}/respawn (record respawn)
    ├─ POST /api/game-events (record objectives, events)
    ├─ POST /api/scores (award points)
    └─ GET /api/announcements (system messages)
    ↓
[WebSocket Connection (Optional)]
    └─ ws://server/ws/live (for push updates)
```

## Data Models & Mapping

### Player Model

**Team Terminals:**
```dart
Player {
  String id
  String name
  String callsign
  TeamType team          // taskForceOnyx | blackTalon
  String role
  List<PlayerReport> reports
}
```

**Server:**
```json
{
  "id": "player-123",
  "username": "john_doe",
  "callsign": "Alpha-1",
  "member_profile_id": 1,
  "user_role_id": 1
}
```

**Mapping:**
- `Player.id` → `Player.id`
- `Player.name` → `Player.username`
- `Player.callsign` → `Player.callsign`
- `Player.role` → Device from `UserRole.name`
- `Player.team` → Inferred from game context

---

### Game Session Model

**Team Terminals:**
```dart
GameSession {
  String id
  String gameModeName
  Map<TeamType, int> respawnCounts
  Map<TeamType, int> respawnLimits
  bool isActive
  DateTime startTime
  DateTime endTime
  String notes
  Map<TeamType, int> objectivesCaptured
}
```

**Server:**
```json
{
  "id": 1,
  "game_session_id": 1,
  "game_mode_id": 5,
  "team_id": 1,
  "status": "active",
  "started_at": "2024-01-15T10:30:00Z",
  "ended_at": null,
  "notes": ""
}
```

**Mapping:**
- `GameSession.id` → `GameSession.id`
- `GameSession.gameModeName` → `GameMode.name`
- `respawnCounts[team]` → Sum of `GameEvent` type "respawn" per team
- `isActive` → `GameSession.status == "active"`

---

### Game Event Model

**Team Terminals Recording:**
```dart
// Handled via Team Terminals comms log
CommsMessage {
  String id
  DateTime timestamp
  String sender
  String text   // "Objective captured by Team Alpha"
  MessageType type  // info | warning | urgent
}
```

**Server:**
```json
{
  "id": 1,
  "game_session_id": 1,
  "event_type": "objective_captured",
  "description": "Team A captured Objective B",
  "team_id": 1,
  "player_id": 5,
  "happened_at": "2024-01-15T10:30:00Z"
}
```

---

## Required Server Endpoints

All endpoints require base URL: `http://server:8000/api`

### Players Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/players?team_id={id}` | Get all players for a team |
| POST | `/players` | Register/update a player |
| GET | `/players/{id}` | Get player details |

### Game Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/game-sessions` | List active sessions |
| POST | `/game-sessions` | Create new session |
| GET | `/game-sessions/{id}` | Get session details |
| POST | `/game-sessions/{id}/respawn` | Record respawn event |
| POST | `/game-sessions/{id}/end` | End session |

### Game Events & Scoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/game-events` | Record game event |
| GET | `/game-events/session/{id}` | Get events timeline |
| POST | `/scores` | Record score |
| GET | `/scores/session/{id}/leaderboard` | Get leaderboard |

### Missions & Schedules

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/missions` | List available missions |
| GET | `/missions/{id}/schedule` | Get mission schedule |

### Announcements

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/announcements/christy` | Get AI announcements |
| POST | `/announcements/create-christy` | Post announcement |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check |

---

## HTTP Request Examples

### 1. Get Team Roster

```bash
curl -X GET "http://server:8000/api/players?team_id=1" \
  -H "Content-Type: application/json"
```

**Response:**
```json
[
  {
    "id": "p1",
    "username": "alice",
    "callsign": "Alpha-1",
    "team": "taskForceOnyx",
    "role": "marksman"
  }
]
```

---

### 2. Start Game Session

```bash
curl -X POST "http://server:8000/api/game-sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "game_mode": "Team Deathmatch",
    "respawn_limits": {
      "taskForceOnyx": 20,
      "blackTalon": 20
    }
  }'
```

**Response:**
```json
{
  "id": "gs-123",
  "game_mode_name": "Team Deathmatch",
  "status": "active",
  "started_at": "2024-01-15T10:30:00Z"
}
```

---

### 3. Record Respawn

```bash
curl -X POST "http://server:8000/api/game-sessions/gs-123/respawn" \
  -H "Content-Type: application/json" \
  -d '{
    "team": "taskForceOnyx"
  }'
```

---

### 4. Record Game Event (Objective Capture)

```bash
curl -X POST "http://server:8000/api/game-events" \
  -H "Content-Type: application/json" \
  -d '{
    "game_session_id": "gs-123",
    "event_type": "objective_captured",
    "description": "Team Alpha captured the main objective",
    "team_id": 1,
    "player_id": 5,
    "metadata": "{}"
  }'
```

---

### 5. Award Score

```bash
curl -X POST "http://server:8000/api/scores" \
  -H "Content-Type: application/json" \
  -d '{
    "game_session_id": "gs-123",
    "team_id": 1,
    "player_id": 5,
    "points": 100,
    "reason": "objective_capture"
  }'
```

---

## Implementation in Team Terminals

### 1. Configure Server Connection

In `AppState`, add server configuration:

```dart
Future<void> connectToServer(String serverHost) async {
  _serverService = ServerIntegrationService(serverHost);
  
  // Test connection
  final connected = await _serverService.testConnection();
  if (connected) {
    _serverConnected = true;
    await _loadServerData();
  }
}
```

### 2. Sync Data on Startup

```dart
Future<void> _loadServerData() async {
  _players = await _serverService.getPlayers(_team.name);
  _gameFiles = await _serverService.getGameSessions();
  notifyListeners();
}
```

### 3. Record Respawn in Real-Time

```dart
Future<void> recordRespawn(String sessionId, TeamType team) async {
  final success = await _serverService.recordRespawn(
    sessionId: sessionId,
    team: team,
  );
  
  if (success) {
    // Update local UI
    _updateRespawnCount(team);
  }
}
```

### 4. Listen for Server Updates (via WebSocket)

```dart
// Optional WebSocket connection for real-time updates
_websocketStream = _serverService.watchSession(sessionId);
_websocketStream.listen((event) {
  // Update respawn counts, scores, etc
  _handleServerUpdate(event);
});
```

---

## Network Configuration

### Development (Local WiFi)

```
Server: 192.168.1.100:8000
Tablets: 192.168.1.101, 192.168.1.102
Network: Private WiFi
```

### Production (Event Venue)

```
Server: Internal IP or VPN address
Tablets: Connected via venue WiFi
Security: API authentication recommended
```

---

## Error Handling

Team Terminals should gracefully handle:

1. **Server Unavailable**
   - Fallback to offline mode (local data)
   - Show connection status indicator
   - Retry connection with backoff

2. **Network Latency**
   - Implement request timeout (10 seconds)
   - Queue operations offline
   - Sync when connection restored

3. **Data Conflicts**
   - Server data takes precedence
   - Local changes conflict with server updates
   - Show conflict resolution UI

---

## Security Considerations

1. **Authentication** (Future)
   - Implement token-based auth (JWT)
   - Secure token storage on device
   - Add session expiration

2. **Network Security**
   - Use HTTPS in production
   - Validate SSL certificates
   - Consider VPN for remote deployments

3. **Data Privacy**
   - Encrypt sensitive data at rest
   - Sanitize player/event information
   - Implement access control

---

## Debugging & Logging

### Enable Network Logging

```dart
// In debug mode, log all HTTP requests/responses
if (kDebugMode) {
  http.Client client = http.Client();
  client = http.LoggingMiddleware(client);
}
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Verify server IP/port configuration |
| "Timeout after 10s" | Check network connectivity & server load |
| "401 Unauthorized" | Verify API authentication (if enabled) |
| "404 Not Found" | Confirm API endpoint exists on server |

---

## Testing Checklist

- [ ] Team Terminals connects to AOJ server on startup
- [ ] Can retrieve player roster from server
- [ ] Can start/end game session
- [ ] Respawn tracking syncs to server
- [ ] Game events logged correctly
- [ ] Leaderboard updates in real-time
- [ ] Offline fallback works properly
- [ ] Reconnection after network interruption works
- [ ] Large event payloads handled correctly
- [ ] Concurrent requests from multiple tablets don't conflict

---

## API Compatibility

| Component | Version | Status |
|-----------|---------|--------|
| AOJ Backend | 1.0.0+ | ✅ Supported |
| Team Terminals | 1.0.0+ | ✅ Compatible |
| Flutter | 3.11.5+ | ✅ Tested |
| HTTP Protocol | HTTP/1.1 | ✅ Used |

---

## Future Enhancements

1. **WebSocket Real-time Sync** - Remove polling, use push notifications
2. **Offline Queue** - Queue operations while offline, sync when online
3. **Multi-server Support** - Connect to backup servers for failover
4. **Role-based Access** - Different permissions for admin vs. player tabs
5. **End-to-end Encryption** - For sensitive event information
6. **Mobile App Notifications** - Push notifications for game events

