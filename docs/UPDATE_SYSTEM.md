# AOJ Command OS Update System

## Purpose

The Update Center module exists to make field maintenance safer on a Raspberry Pi appliance.

Current goals:
- show running version information
- show database path and latest backup
- allow safe database backup creation
- support in-place firmware package upload and prop rollout without reinstalling AOJ
- reserve future flows for full core-app restore and rollback

## Current Implementation

Backend route prefix:
- `/api/update-center`

Implemented endpoints:
- `GET /status`
- `POST /backup`
- `GET /firmware-packages`
- `POST /firmware-upload`
- `POST /firmware-apply`
- `POST /upload-placeholder`
- `POST /restore-placeholder`
- `POST /rollback-placeholder`

Current service file:
- `backend/app/services/update_center_service.py`

## What Works Today

### Status Reporting

The status endpoint reports:
- system version
- frontend version from `frontend/package.json`
- backend version from the backend service
- database version from SQLite `PRAGMA user_version`
- database file path
- latest backup file name
- firmware package count
- last firmware upload timestamp
- changelog list

This gives an operator enough information to verify what build is currently on the Raspberry Pi.

### Database Backup

The backup endpoint creates a timestamped copy of the SQLite database.

Stored in:
- `backend/backups/`

This is a real action, not a placeholder.

When a backup is created:
- the database file is copied
- an `UPDATE` category system log is written

### Firmware Package Upload and Rollout

Firmware updates can now be queued without reinstalling the AOJ server.

Current behavior:
- stores uploaded firmware binaries in `backend/firmware/packages/`
- records package metadata in `backend/firmware/index.json`
- exposes package history through `GET /firmware-packages`
- applies selected firmware packages to target props (or all props) through `POST /firmware-apply`
- queues LoRa command `FIRMWARE_UPDATE` with version/package payload
- updates target prop records to maintenance state and new firmware version
- writes update logs for upload and rollout events

This flow updates field devices in place and avoids deleting/reinstalling the AOJ application itself.

## What Is Still a Placeholder

The following core-system actions intentionally do not modify runtime files:

### Upload Package Placeholder

Current behavior:
- accepts metadata about an offline package
- logs the request
- returns a placeholder response

Why it is not live yet:
- there is no signature validation flow
- there is no staged extraction and verification flow
- there is no safe file swap procedure implemented

### Restore Placeholder

Current behavior:
- logs the restore request
- returns a response confirming no database files were changed

Why it is not live yet:
- restore must verify compatibility and require explicit approval
- a live in-place swap can corrupt an active field appliance if done poorly

### Rollback Placeholder

Current behavior:
- logs the rollback request
- returns a response confirming no files were changed

Why it is not live yet:
- rollback requires version manifests, staged backups, and approval checks

## Why the System Is Conservative

AOJ Command OS is intended for live event use. An unsafe update flow could:
- break the backend before a game starts
- corrupt results or schedule data
- leave staff without a usable dashboard during the day

For that reason, the project currently allows only the safest real operation: database backup.

## Operational Policy

Recommended field policy:

1. Do not attempt software upgrades during an active round.
2. Always create a database backup before maintenance.
3. Perform updates before the event day or during a clear admin-only maintenance window.
4. Keep one known-good release archive outside the Raspberry Pi.
5. Record who performed the maintenance and when.

## Suggested Offline Update Workflow for the Future

Recommended safe future design:

1. Operator uploads a signed update package.
2. The system validates the package signature and manifest.
3. Files are extracted into a staging directory, not the live runtime path.
4. The system checks backend and frontend versions, schema requirements, and compatibility rules.
5. The system creates a fresh database backup.
6. The operator confirms the maintenance window.
7. The system switches to the new version atomically or near-atomically.
8. Health checks verify backend and frontend startup.
9. Rollback is offered only if the new version fails validation.

## Changelog Source

The current changelog is static in the backend service.

Future improvement:
- generate changelog metadata from signed release manifests rather than hard-coded strings

## Backup Strategy

Two backup paths currently exist:
- API-driven backup from the Update Center module
- shell backup using `scripts/backup_database.sh`

Recommended habit:
- use the API for operator-visible backups
- use the shell script for maintenance and scheduled cron-style backups

## Failure Scenarios to Design Around

Any future real update implementation should protect against:
- power loss during file replacement
- schema mismatch between code and database
- incomplete frontend build assets
- invalid Python dependencies
- rollback to an incompatible database version

## Current Limitations

- Firmware command dispatch is queued; delivery/ACK success depends on LoRa transport health
- No signed firmware manifest validation yet
- No full core-app restore implementation
- No full core-app rollback implementation
- No authentication or approval enforcement

## Minimum Safe Next Steps

If this module is extended, the next safe improvements are:

1. Add signed package manifest validation.
2. Add staged extraction outside runtime directories.
3. Add explicit admin approval requirements.
4. Add preflight health checks and post-install verification.
5. Add versioned rollback metadata instead of ad hoc file swapping.