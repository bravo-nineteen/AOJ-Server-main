# AOJ Command OS User Roles

## Current Status

AOJ Command OS currently contains a `user_roles` database table for role definitions, but it does not yet enforce authentication or role-based access control in API routes.

This document defines the practical role model the system is aiming toward for airsoft field operations.

## Why Roles Matter

At an airsoft field, not every staff member should be able to:
- start or end a mission
- arm or reset props
- restore backups
- approve updates
- change scoring after a round ends

Even before route-level enforcement exists, role definitions help the team standardize who is allowed to do what.

## Recommended Roles

### Admin

Purpose:
- Full system administration and final authority

Typical responsibilities:
- Deploy the Raspberry Pi appliance
- Configure services and networking
- Approve updates and backup procedures
- Review logs and diagnose faults
- Override operational decisions when necessary

Recommended permissions:
- full Mission Control actions
- full Prop Network actions
- schedule editing
- results editing
- system log access
- system monitor access
- AI assistant access
- update center backup, upload, restore, and rollback permissions
- future user and role management

### Game Marshal

Purpose:
- Run the live game flow on the day

Typical responsibilities:
- start, pause, resume, and end matches
- adjust objectives and scores
- coordinate round transitions

Recommended permissions:
- Mission Control read and write
- schedule read
- limited schedule update if your field allows it
- Prop Network command permissions for approved prop actions
- system log read
- results create and finalize
- AI assistant use for briefings or summaries

### Scorekeeper

Purpose:
- Record results, penalties, and match outcomes

Typical responsibilities:
- update scores after marshal confirmation
- maintain results history
- assist with schedule accuracy

Recommended permissions:
- Mission Control read
- Results Board read and write
- schedule read
- system logs read
- no prop control
- no update permissions

### Prop Technician

Purpose:
- Manage field devices and troubleshooting

Typical responsibilities:
- register props
- inspect battery and signal status
- send test or reset commands during setup or maintenance windows
- diagnose faulty field devices

Recommended permissions:
- Prop Network read and write
- System Monitor read
- System Logs read
- no mission start or end authority by default
- no update restore or rollback by default

### Observer / Read-Only Staff

Purpose:
- View the operational picture without changing state

Typical responsibilities:
- view schedule
- view mission status
- view results and logs

Recommended permissions:
- read-only access across most modules
- no destructive or state-changing actions

## Suggested Permission Groups

The current `permissions` field is stored as text. A simple JSON array is a practical near-term format.

Example:

```json
[
  "mission.read",
  "mission.control",
  "schedule.read",
  "results.write",
  "prop.command"
]
```

Recommended permission names:
- `mission.read`
- `mission.control`
- `mission.score.write`
- `mission.objective.write`
- `schedule.read`
- `schedule.write`
- `results.read`
- `results.write`
- `prop.read`
- `prop.write`
- `prop.command`
- `logs.read`
- `monitor.read`
- `ai.ask`
- `update.read`
- `update.backup`
- `update.upload`
- `update.restore`
- `update.rollback`
- `admin.full`

## Practical Field Policy

Even before technical enforcement exists, use operational policy:

1. Only one or two staff should hold Admin authority.
2. Game start and end actions should be limited to lead marshals.
3. Prop reset and arm workflows should require a marshal or admin confirmation step.
4. Restore and rollback actions should never be attempted during an active round.
5. Score adjustments after match end should require a visible audit note.

## Mapping Roles to Current Modules

### Mission Control

Recommended write access:
- Admin
- Game Marshal

Recommended read access:
- Scorekeeper
- Observer

### Schedule

Recommended write access:
- Admin
- Lead Marshal

Recommended read access:
- all staff roles

### Results Board

Recommended write access:
- Scorekeeper
- Admin
- Lead Marshal if needed

### Prop Network

Recommended write access:
- Prop Technician
- Admin
- Marshal during live rounds only if the field procedure allows it

### System Logs and Monitor

Recommended read access:
- Admin
- Prop Technician
- Lead Marshal

### AI Assistant

Recommended access:
- Admin
- Marshal
- Scorekeeper

The AI assistant is advisory-only and should never be treated as an authority for live command execution.

### Update Center

Recommended access:
- Read status: Admin only, or Admin plus technical staff
- Backup: Admin only
- Restore and rollback: Admin only, off-game, with backup confirmed

## Implementation Notes for Future RBAC

To make this real in code later, add:
- user identity model
- login or local operator session mechanism
- route dependency checks for permission scopes
- action audit logs tied to operator identity

Minimum safe first step:
- enforce update, prop command, and mission control write actions before read-only views