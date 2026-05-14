# Props Network & Game Mode Integration

## ✅ Status: Complete

All current props are now in the network AND can be assigned to games with 12 new game mode types.

---

## 🎯 What's New

### 1. **All 9 Props Now Visible in Network**

| # | Device ID | Name | Type | Firmware |
|---|-----------|------|------|----------|
| 1 | BD-001 | CSGO Bomb | Bomb | 1.3.8 |
| 2 | VEST-001 | Bomb Vest | Bomb Vest | 1.2.0 |
| 3 | CASE-001 | Briefcase Bomb | Briefcase Bomb | 1.1.0 |
| 4 | DOM-001 | Domination Point A | Domination Point | 1.0.0 |
| 5 | DOM-002 | Domination Point B | Domination Point | 1.0.0 |
| 6 | RESP-001 | Respawn Station Alpha | Respawn Station | 1.0.0 |
| 7 | RESP-002 | Respawn Station Bravo | Respawn Station | 1.0.0 |
| 8 | GM-001 | Game Master Unit | Game Master Unit | 1.0.0 |
| 9 | CP-001 | Control Panel Unit | Control Panel Unit | 1.0.0 |

**API:** `GET /api/props` - Returns all props in network

---

### 2. **12 New Game Mode Types**

All available game modes are now automatically seeded on startup:

1. **Bomb Defusal** - Attackers plant the bomb, defenders defuse
2. **Capture the Flag** - Teams capture enemy flag to their base
3. **Deathmatch** - Free-for-all combat (highest eliminations wins)
4. **Domination** - Control multiple objective points
5. **Elimination** - Single lives per round
6. **Hacking** - Hack/secure data points on the map
7. **Hostage Rescue** - Rescue hostages held by terrorists
8. **King of the Hill** - Maintain control of central area
9. **Search and Destroy** - Hybrid bomb + team elimination
10. **Team Deathmatch** - Team-based combat mode
11. **Team Fortress** - One team defends fortress, other attacks
12. **VIP Escort** - Protect/eliminate designated VIP player

**API:** `GET /api/game-sessions/game-modes/list` - Lists all 12 game modes

---

### 3. **Props → Games Assignment**

#### Endpoints Added:

**Assign Props to Game Sessions:**
- `POST /api/game-sessions/{session_id}/props/{prop_id}` - Assign single prop
- `POST /api/game-sessions/{session_id}/props/bulk-assign` - Assign multiple props
- `POST /api/game-sessions/{session_id}/props/by-type` - Assign by prop type
- `DELETE /api/game-sessions/{session_id}/props/{prop_id}` - Unassign prop
- `GET /api/game-sessions/{session_id}/props` - View props in session

**Game Session Management:**
- `POST /api/game-sessions` - Create new game session
- `GET /api/game-sessions` - List all sessions
- `GET /api/game-sessions/{session_id}` - Get session details
- `PUT /api/game-sessions/{session_id}` - Update session
- `DELETE /api/game-sessions/{session_id}` - Delete session

---

## 📊 Database Relationships

### New Association Table
```sql
CREATE TABLE game_session_props (
    game_session_id INTEGER,
    prop_id INTEGER,
    PRIMARY KEY (game_session_id, prop_id),
    FOREIGN KEY (game_session_id) REFERENCES game_sessions(id),
    FOREIGN KEY (prop_id) REFERENCES props(id)
)
```

### Relationship Flow
```
GameSession ←→ Prop (Many-to-Many)
   ↓
GameMode
   ↓
PropType (10 types)
   ↓
Device Communication (LoRa)
```

---

## 🔌 Example Usage

### Create a Game Session
```bash
POST /api/game-sessions
{
  "name": "Mission Alpha - Bomb Defusal",
  "game_mode_id": 1,
  "is_active": true,
  "main_timer_seconds": 1800
}
```

### Assign Props to Game
```bash
POST /api/game-sessions/1/props/bulk-assign
{
  "prop_ids": [1, 2, 3]
}
```

### Assign All Bombs to Game
```bash
POST /api/game-sessions/1/props/by-type
{
  "prop_types": ["Bomb", "Bomb Vest", "Briefcase Bomb"]
}
```

### View Props in Game
```bash
GET /api/game-sessions/1/props
```

Returns:
```json
{
  "session_id": 1,
  "session_name": "Mission Alpha - Bomb Defusal",
  "prop_count": 3,
  "props": [
    {
      "id": 1,
      "device_id": "BD-001",
      "name": "CSGO Bomb",
      "prop_type": "Bomb",
      "status": "online",
      "battery_level": 85,
      "signal_strength": 90
    },
    ...
  ]
}
```

---

## 📦 Files Modified/Created

### New Files
- `backend/app/services/game_mode_init_service.py` - Game mode seeding & management
- `backend/app/routes/game_sessions.py` - Game session & prop assignment endpoints

### Modified Files
- `backend/app/models/game_session.py` - Added props relationship
- `backend/app/models/prop.py` - Added game_sessions relationship
- `backend/app/schemas/game_session.py` - Added GameSessionUpdate schema
- `backend/app/routes/__init__.py` - Added game_sessions import
- `backend/app/main.py` - Game mode initialization + route registration

### Code Statistics
- **12 Game Modes** defined with rules, timers, prop requirements
- **9 Props** automatically initialized per startup
- **11 New API Endpoints** for game session & prop management
- **Relationships:** Many-to-many association between GameSession ↔ Prop

---

## 🚀 WebSocket Events

Props assignment now broadcasts events:

```javascript
{
  "event": "game_session.prop_assigned",
  "payload": {
    "session_id": 1,
    "prop_id": 1,
    "device_id": "BD-001",
    "prop_name": "CSGO Bomb"
  }
}

{
  "event": "game_session.prop_unassigned",
  "payload": {
    "session_id": 1,
    "prop_id": 1,
    "device_id": "BD-001"
  }
}

{
  "event": "game_session.props_bulk_assigned",
  "payload": {
    "session_id": 1,
    "assigned_count": 3,
    "failed_count": 0
  }
}
```

---

## ✨ Features Included

✅ **Props Network Display** - All 9 devices visible with status
✅ **Game Mode Types** - 12 game modes auto-seeded on startup
✅ **Props ↔ Games** - Assign/unassign props to game sessions
✅ **Bulk Operations** - Assign multiple props or by type
✅ **Session Management** - Create, read, update, delete sessions
✅ **Real-time Updates** - WebSocket events on prop assignment
✅ **Relationship Tracking** - Database maintains many-to-many links
✅ **Logging** - All operations logged with categories

---

## 🔧 Initialization

Automatic on startup:
1. Creates 12 game mode entries in database
2. Seeds 9 props (if not already present)
3. Logs initialization statistics
4. Ready for immediate game session creation

**Log Output:**
```
Device initialization complete: 0 created, 9 existing
Game mode initialization complete: 12 created, 0 existing
```

