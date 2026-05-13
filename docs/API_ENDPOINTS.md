# AOJ Backend API Endpoints Documentation

## Overview

This document describes the new RESTful API endpoints added to the AOJ Command OS backend. These endpoints provide comprehensive management of game events, scoring, announcements, missions, game modes, firmware rollouts, and system logs.

## Base URL

All endpoints are prefixed with `/api/`

## Authentication

Currently, endpoints do not require authentication. This should be implemented for production deployment.

---

## Game Events & Objectives

Base URL: `/api/game-events`

### Record a Game Event

**Endpoint:** `POST /api/game-events`

**Description:** Record an event during active gameplay (objective capture, deployment, etc).

**Request Body:**
```json
{
  "event_type": "objective_captured",
  "description": "Team A captured Objective B",
  "metadata": "{}",
  "game_session_id": 1,
  "team_id": 1,
  "player_id": 5,
  "squad_id": null,
  "device_id": null,
  "prop_id": null
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "event_type": "objective_captured",
  "description": "Team A captured Objective B",
  "metadata": "{}",
  "game_session_id": 1,
  "team_id": 1,
  "player_id": 5,
  "squad_id": null,
  "device_id": null,
  "prop_id": null,
  "happened_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Session Events (Game Timeline)

**Endpoint:** `GET /api/game-events/session/{session_id}`

**Description:** Get all events for a game session in chronological order.

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "event_type": "objective_captured",
    "description": "Team A captured Objective B",
    "happened_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z",
    "game_session_id": 1,
    "team_id": 1,
    "player_id": 5,
    "squad_id": null,
    "device_id": null,
    "prop_id": null,
    "metadata": "{}"
  }
]
```

### Get Objective Events

**Endpoint:** `GET /api/game-events/session/{session_id}/objectives`

**Description:** Get objective-related events for a session.

**Response:** `200 OK`
Returns events filtered to objective events only (captured, lost, completed).

### Get Team Events

**Endpoint:** `GET /api/game-events/team/{team_id}/events?session_id={session_id}`

**Description:** Get all events for a team in a session.

**Query Parameters:**
- `session_id` (required): Game session ID

**Response:** `200 OK`

### Get Player Events

**Endpoint:** `GET /api/game-events/player/{player_id}/events?session_id={session_id}`

**Description:** Get all events involving a player in a session.

**Query Parameters:**
- `session_id` (required): Game session ID

**Response:** `200 OK`

---

## Scoring & Leaderboards

Base URL: `/api/scores`

### Record a Score Event

**Endpoint:** `POST /api/scores`

**Description:** Record a score event (points awarded).

**Request Body:**
```json
{
  "game_session_id": 1,
  "team_id": 1,
  "player_id": 5,
  "points": 100,
  "reason": "objective_capture"
}
```

**Response:** `201 Created`

### Get Session Leaderboard

**Endpoint:** `GET /api/scores/session/{session_id}/leaderboard`

**Description:** Get player leaderboard for a session sorted by total score.

**Response:** `200 OK`
```json
[
  {
    "player_id": 5,
    "username": "player_name",
    "total_score": 450
  },
  {
    "player_id": 3,
    "username": "another_player",
    "total_score": 350
  }
]
```

### Get Team Scores

**Endpoint:** `GET /api/scores/team/{team_id}/session/{session_id}`

**Description:** Get all score events for a team in a session.

**Response:** `200 OK`

### Get Player Scores

**Endpoint:** `GET /api/scores/player/{player_id}/session/{session_id}`

**Description:** Get all scores for a player in a session.

**Response:** `200 OK`

### Get Score Breakdown

**Endpoint:** `GET /api/scores/session/{session_id}/by-reason`

**Description:** Get scoring breakdown by reason for a session.

**Response:** `200 OK`
```json
{
  "objective_capture": 500,
  "elimination": 300,
  "mission_complete": 200
}
```

---

## Announcements & Notifications

Base URL: `/api/announcements`

### Create Christy Announcement

**Endpoint:** `POST /api/announcements/create-christy`

**Description:** Create a Christy (AI character) announcement.

**Request Body:**
```json
{
  "type": "general",
  "content": "The objective has been captured!"
}
```

**Response:** `201 Created`

### Create Announcement Rule

**Endpoint:** `POST /api/announcements/rule`

**Description:** Create an announcement rule (trigger-based).

**Request Body:**
```json
{
  "name": "Objective Warning",
  "enabled": true,
  "trigger_activity_types": "objective_capture",
  "trigger_minutes_before": 5,
  "message_template": "Team {team_name} is about to capture objective {objective_name}!"
}
```

**Response:** `201 Created`

### List Christy Announcements

**Endpoint:** `GET /api/announcements/christy?limit=50`

**Description:** List Christy announcements (most recent first).

**Query Parameters:**
- `limit` (optional, default=50, max=1000): Max number of announcements to return

**Response:** `200 OK`

### List Announcement Rules

**Endpoint:** `GET /api/announcements/rules?status=active`

**Description:** List announcement rules.

**Query Parameters:**
- `status` (optional): Filter by "active" or "inactive"

**Response:** `200 OK`

### Update Announcement Rule

**Endpoint:** `PUT /api/announcements/rules/{rule_id}`

**Description:** Update an announcement rule.

**Request Body:**
```json
{
  "name": "Updated Rule Name",
  "enabled": false
}
```

**Response:** `200 OK`

### Delete Announcement Rule

**Endpoint:** `DELETE /api/announcements/rules/{rule_id}`

**Description:** Delete an announcement rule.

**Response:** `204 No Content`

---

## Missions

Base URL: `/api/missions`

### Create Mission

**Endpoint:** `POST /api/missions`

**Description:** Create a new mission.

**Request Body:**
```json
{
  "name": "Capture the Flag",
  "description": "Teams compete to capture and hold the flag",
  "game_mode_id": 1
}
```

**Response:** `201 Created`

### List Missions

**Endpoint:** `GET /api/missions`

**Description:** List all missions.

**Response:** `200 OK`

### Get Mission

**Endpoint:** `GET /api/missions/{mission_id}`

**Description:** Get a specific mission.

**Response:** `200 OK`

### Update Mission

**Endpoint:** `PUT /api/missions/{mission_id}`

**Description:** Update a mission.

**Request Body:** Same as POST

**Response:** `200 OK`

### Delete Mission

**Endpoint:** `DELETE /api/missions/{mission_id}`

**Description:** Delete a mission.

**Response:** `204 No Content`

### Get Mission Results

**Endpoint:** `GET /api/missions/{mission_id}/results`

**Description:** Get all game results for a mission.

**Response:** `200 OK`

---

## Game Modes

Base URL: `/api/game-modes`

### Create Game Mode

**Endpoint:** `POST /api/game-modes`

**Description:** Create a new game mode.

**Request Body:**
```json
{
  "name": "Team Deathmatch",
  "description": "Teams eliminate each other",
  "default_main_timer_seconds": 1800,
  "default_phase_timer_seconds": 300,
  "rules": "{}"
}
```

**Response:** `201 Created`

### List Game Modes

**Endpoint:** `GET /api/game-modes`

**Description:** List all game modes.

**Response:** `200 OK`

### Get Game Mode

**Endpoint:** `GET /api/game-modes/{mode_id}`

**Description:** Get a specific game mode.

**Response:** `200 OK`

### Update Game Mode

**Endpoint:** `PUT /api/game-modes/{mode_id}`

**Description:** Update a game mode.

**Request Body:** Same as POST

**Response:** `200 OK`

### Delete Game Mode

**Endpoint:** `DELETE /api/game-modes/{mode_id}`

**Description:** Delete a game mode.

**Response:** `204 No Content`

---

## Firmware Rollouts

Base URL: `/api/firmware-rollouts`

### List Firmware Rollouts

**Endpoint:** `GET /api/firmware-rollouts?status=in_progress`

**Description:** List firmware rollouts.

**Query Parameters:**
- `status` (optional): Filter by status (queued, in_progress, completed, cancelled)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "package_id": "pkg-123",
    "package_version": "1.2.3",
    "package_filename": "firmware-1.2.3.bin",
    "status": "completed",
    "targeted_count": 10,
    "acknowledged_count": 10,
    "failed_count": 0,
    "targets": [],
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z"
  }
]
```

### Get Firmware Rollout

**Endpoint:** `GET /api/firmware-rollouts/{rollout_id}`

**Description:** Get a specific firmware rollout.

**Response:** `200 OK`

### Start Firmware Rollout

**Endpoint:** `POST /api/firmware-rollouts/{rollout_id}/start`

**Description:** Start a firmware rollout.

**Response:** `200 OK`

### Complete Firmware Rollout

**Endpoint:** `POST /api/firmware-rollouts/{rollout_id}/complete`

**Description:** Complete a firmware rollout.

**Response:** `200 OK`

### Cancel Firmware Rollout

**Endpoint:** `POST /api/firmware-rollouts/{rollout_id}/cancel`

**Description:** Cancel a firmware rollout.

**Response:** `200 OK`

---

## System Logs

Base URL: `/api/system-logs`

### List System Logs

**Endpoint:** `GET /api/system-logs?level=info&category=mission&limit=100`

**Description:** List system logs with optional filtering.

**Query Parameters:**
- `level` (optional): Filter by level (debug, info, warning, error, critical)
- `category` (optional): Filter by category (system, mission, lora, etc.)
- `source` (optional): Filter by source
- `limit` (optional, default=100, max=1000): Max number of logs to return
- `offset` (optional, default=0): Pagination offset

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "level": "info",
    "category": "mission",
    "source": "game_events",
    "message": "Event: objective_captured - Team A captured objective",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Logs by Category

**Endpoint:** `GET /api/system-logs/by-category`

**Description:** Get count of logs grouped by category.

**Response:** `200 OK`
```json
{
  "system": 45,
  "mission": 123,
  "lora": 78
}
```

### Get Logs by Source

**Endpoint:** `GET /api/system-logs/by-source`

**Description:** Get count of logs grouped by source.

**Response:** `200 OK`
```json
{
  "game_events": 50,
  "firmware": 30,
  "announcements": 20
}
```

---

## System Settings

Base URL: `/api/system-settings`

### Create or Update System Setting

**Endpoint:** `POST /api/system-settings`

**Description:** Create or update a system setting.

**Request Body:**
```json
{
  "key": "max_players_per_team",
  "value": "4",
  "description": "Maximum number of players allowed per team"
}
```

**Response:** `201 Created` or `200 OK`

### List System Settings

**Endpoint:** `GET /api/system-settings`

**Description:** List all system settings.

**Response:** `200 OK`
```json
[
  {
    "key": "max_players_per_team",
    "value": "4",
    "description": "Maximum number of players allowed per team",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
]
```

### Get System Setting

**Endpoint:** `GET /api/system-settings/{setting_key}`

**Description:** Get a specific system setting by key.

**Response:** `200 OK`

### Update System Setting

**Endpoint:** `PUT /api/system-settings/{setting_key}`

**Description:** Update a system setting.

**Request Body:**
```json
{
  "key": "max_players_per_team",
  "value": "5",
  "description": "Updated description"
}
```

**Response:** `200 OK`

### Delete System Setting

**Endpoint:** `DELETE /api/system-settings/{setting_key}`

**Description:** Delete a system setting.

**Response:** `204 No Content`

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful GET/PUT request
- `201 Created`: Successful POST request (resource created)
- `204 No Content`: Successful DELETE request
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a detail message:
```json
{
  "detail": "Description of the error"
}
```

---

## Pagination

Endpoints that return lists support pagination:

- `limit`: Number of items to return (default varies by endpoint)
- `offset`: Number of items to skip

Example:
```
GET /api/system-logs?limit=50&offset=100
```

---

## Data Types

### Game Event Types
- `objective_captured`
- `objective_lost`
- `objective_completed`
- `player_eliminated`
- `team_win`
- `team_lose`
- `mission_start`
- `mission_end`

### Log Levels
- `debug`
- `info`
- `warning`
- `error`
- `critical`

### Log Categories
- `system`
- `mission`
- `lora`
- `device`
- `firmware`

### Firmware Statuses
- `queued`
- `in_progress`
- `completed`
- `cancelled`

---

## Integration Examples

### Record a Game Event with Score

```bash
# 1. Record an event
curl -X POST http://localhost:8000/api/game-events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "objective_captured",
    "description": "Team A captured objective X",
    "game_session_id": 1,
    "team_id": 1,
    "player_id": 5,
    "metadata": "{}"
  }'

# 2. Award score for the event
curl -X POST http://localhost:8000/api/scores \
  -H "Content-Type: application/json" \
  -d '{
    "game_session_id": 1,
    "team_id": 1,
    "player_id": 5,
    "points": 100,
    "reason": "objective_capture"
  }'

# 3. View leaderboard
curl http://localhost:8000/api/scores/session/1/leaderboard
```

### Create Announcement Rule

```bash
curl -X POST http://localhost:8000/api/announcements/rule \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Objective Warning",
    "enabled": true,
    "trigger_activity_types": "",
    "trigger_minutes_before": 15,
    "message_template": "Prepare! Objective capture will start in 15 minutes"
  }'
```

### View Mission Results

```bash
curl http://localhost:8000/api/missions/1 \
  && curl http://localhost:8000/api/missions/1/results
```

---

## Notes

- All timestamps are in UTC (ISO 8601 format)
- The `metadata` field can store arbitrary JSON strings for extensibility
- Logging is automatic for significant events
- System settings are case-sensitive for keys
- Firmware rollout processes are managed asynchronously

