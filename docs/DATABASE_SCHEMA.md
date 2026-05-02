# AOJ Command OS Database Schema

## Overview

AOJ Command OS uses SQLite with SQLAlchemy models. The database file is stored at:

- `backend/aoj_command_os.db`

The schema is created automatically on backend startup. A small amount of compatibility upgrading is also handled in code for existing SQLite files.

## Tables

### `devices`

Purpose:
- Tracks network-visible or managed devices associated with the system

Columns:
- `id`: integer primary key
- `name`: device name
- `device_type`: free-form device classification
- `ip_address`: unique IP address
- `status`: enum `online`, `offline`, `maintenance`
- `last_seen`: last heartbeat or contact time
- `created_at`: creation timestamp

Relationships:
- One-to-many with `score_events`

### `props`

Purpose:
- Stores field prop inventory and operational status shown in the Prop Network module

Columns:
- `id`: integer primary key
- `device_id`: unique prop identifier used for LoRa or field mapping
- `name`: human-friendly prop name
- `prop_type`: enum including Bomb, Domination Point, Respawn Station, Alarm, Sensor, Custom
- `location`: field location label
- `status`: current operational status string
- `battery_level`: integer battery percentage
- `signal_strength`: integer signal percentage or abstract quality score
- `last_seen`: last contact timestamp
- `firmware_version`: prop firmware version string
- `created_at`: creation timestamp
- `updated_at`: last update timestamp

### `missions`

Purpose:
- Defines high-level missions or scenarios

Columns:
- `id`: integer primary key
- `title`: mission title
- `description`: longer mission description
- `status`: enum `planned`, `active`, `complete`
- `start_time`: mission start timestamp
- `end_time`: mission end timestamp
- `created_at`: creation timestamp

Relationships:
- One-to-many with `game_sessions`
- One-to-many with `schedule_items`

### `game_sessions`

Purpose:
- Represents a specific playable round or session linked to a mission

Columns:
- `id`: integer primary key
- `mission_id`: nullable foreign key to `missions.id`
- `name`: session name
- `is_active`: boolean active flag
- `start_time`: session start timestamp
- `end_time`: session end timestamp

Relationships:
- Many-to-one with `missions`
- One-to-many with `teams`
- One-to-many with `score_events`
- One-to-many with `game_results`

### `teams`

Purpose:
- Stores team identities for a session

Columns:
- `id`: integer primary key
- `game_session_id`: foreign key to `game_sessions.id`
- `name`: team name
- `callsign`: short callsign or label

Relationships:
- Many-to-one with `game_sessions`
- One-to-many with `score_events`

### `score_events`

Purpose:
- Captures point-affecting events during a session

Columns:
- `id`: integer primary key
- `game_session_id`: foreign key to `game_sessions.id`
- `team_id`: foreign key to `teams.id`
- `device_id`: nullable foreign key to `devices.id`
- `points`: integer point delta
- `event_type`: label for the scoring event
- `happened_at`: event timestamp

Relationships:
- Many-to-one with `game_sessions`
- Many-to-one with `teams`
- Many-to-one with `devices`

### `game_results`

Purpose:
- Stores completed round outcomes for the Results Board

Columns:
- `id`: integer primary key
- `game_session_id`: nullable foreign key to `game_sessions.id`
- `session_name`: stored session label for historical display
- `winner`: enum `Red`, `Blue`, `Draw`, `Cancelled`
- `red_points`: integer score
- `blue_points`: integer score
- `red_penalties`: integer penalty value
- `blue_penalties`: integer penalty value
- `notes`: free-form result notes
- `created_at`: creation timestamp

Relationships:
- Many-to-one with `game_sessions`

### `schedule_items`

Purpose:
- Stores the event schedule for rounds, breaks, briefings, and custom activities

Columns:
- `id`: integer primary key
- `mission_id`: nullable foreign key to `missions.id`
- `title`: schedule title
- `details`: descriptive notes
- `activity_type`: free-form type such as Game, Break, Briefing, Custom
- `start_time`: planned start time
- `end_time`: planned end time
- `is_complete`: boolean completion flag
- `completed_at`: completion timestamp
- `scheduled_for`: legacy or compatibility scheduling field

Relationships:
- Many-to-one with `missions`

Compatibility note:
- Startup code backfills newer columns on older SQLite files using `ALTER TABLE` where possible.

### `system_logs`

Purpose:
- Records operational events and audit-style messages

Columns:
- `id`: integer primary key
- `level`: enum `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `category`: enum `SYSTEM`, `MISSION`, `PROP`, `LORA`, `WIFI`, `AI`, `UPDATE`
- `source`: source component name
- `message`: log message text
- `created_at`: creation timestamp

Compatibility note:
- Startup code adds the `category` column if it is missing on older databases.

### `user_roles`

Purpose:
- Stores role definitions and permission lists

Columns:
- `id`: integer primary key
- `role_name`: unique role name
- `permissions`: JSON-like text payload stored as text
- `is_active`: boolean active flag
- `created_at`: creation timestamp

Important limitation:
- These role records are not currently enforced by an authentication layer. They are data definitions for future RBAC work.

## Relationship Summary

```text
missions -> game_sessions -> teams
missions -> schedule_items
game_sessions -> score_events
game_sessions -> game_results
devices -> score_events
```

The `props` table is currently standalone and used mainly by the Prop Network module.

## Operational Notes

### Why SQLite

SQLite fits the current deployment model because AOJ Command OS runs as a single-node field appliance on a Raspberry Pi.

Advantages:
- Easy to deploy
- Easy to back up
- No separate database server to manage on game day

### Backups

Database backups are created by the Update Center service and by the `scripts/backup_database.sh` script.

Stored in:
- `backend/backups/`

### Schema Management

Current schema management approach:
- SQLAlchemy `create_all()` for base creation
- manual compatibility upgrades in `backend/app/database.py`

Current limitation:
- There is no Alembic migration history yet

If schema evolution becomes more frequent, add real migrations.

## Suggested Future Improvements

- Add indexes for common operational queries if data volume grows
- Normalize prop telemetry history into a separate table
- Add user accounts and session tables for authentication
- Add audit records for sensitive actions such as updates and restores
- Replace text-based `permissions` with a more structured RBAC model if enforcement becomes complex