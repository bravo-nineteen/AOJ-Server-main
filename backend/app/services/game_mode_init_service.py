"""Game mode initialization and management service."""

from sqlalchemy.orm import Session

from app.models import GameMode

# Default game modes with their configurations
DEFAULT_GAME_MODES = [
    {
        "name": "Deathmatch",
        "description": "Free-for-all combat where each player competes individually. Highest eliminations wins.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": False,
            "scoring": "eliminations",
            "respawn": True,
            "props_used": ["alarm", "sensor"],
        },
    },
    {
        "name": "Team Deathmatch",
        "description": "Team-based combat mode. Teams compete to reach elimination target.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "team_eliminations",
            "respawn": True,
            "props_used": ["alarm", "sensor"],
        },
    },
    {
        "name": "Capture the Flag",
        "description": "Teams must capture and return the enemy flag to their base.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 400,
        "rules": {
            "team_mode": True,
            "scoring": "flag_captures",
            "respawn": True,
            "props_used": ["domination_point", "respawn_station", "alarm"],
        },
    },
    {
        "name": "Bomb Defusal",
        "description": "Attackers plant the bomb at a target location, defenders must prevent or defuse it.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "bomb_plants_defusals",
            "respawn": False,
            "props_used": ["bomb", "briefcase_bomb", "respawn_station"],
        },
    },
    {
        "name": "Hostage Rescue",
        "description": "Terrorists hold hostages, counter-terrorists must rescue them.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 400,
        "rules": {
            "team_mode": True,
            "scoring": "hostages_rescued",
            "respawn": False,
            "props_used": ["respawn_station", "alarm"],
        },
    },
    {
        "name": "Domination",
        "description": "Teams compete to control multiple objective points on the map.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 400,
        "rules": {
            "team_mode": True,
            "scoring": "points_held",
            "respawn": True,
            "props_used": ["domination_point", "respawn_station"],
        },
    },
    {
        "name": "King of the Hill",
        "description": "Teams must maintain control of a central objective area.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "time_in_zone",
            "respawn": True,
            "props_used": ["domination_point", "respawn_station"],
        },
    },
    {
        "name": "VIP Escort",
        "description": "One player is designated VIP and must be protected/eliminated.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "vip_protection",
            "respawn": False,
            "props_used": ["gm_unit", "alarm"],
        },
    },
    {
        "name": "Hacking",
        "description": "Teams must hack/secure data points scattered across the map.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 400,
        "rules": {
            "team_mode": True,
            "scoring": "data_points_hacked",
            "respawn": True,
            "props_used": ["cp_unit", "domination_point"],
        },
    },
    {
        "name": "Team Fortress",
        "description": "One team defends a fortress while the other attacks to breach it.",
        "default_main_timer_seconds": 2400,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "fortress_breach",
            "respawn": True,
            "props_used": ["domination_point", "alarm", "respawn_station"],
        },
    },
    {
        "name": "Elimination",
        "description": "Single lives per round. Last team/player standing wins each round.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "rounds_won",
            "respawn": False,
            "props_used": ["alarm", "sensor"],
        },
    },
    {
        "name": "Search and Destroy",
        "description": "Hybrid of bomb defusal and team elimination.",
        "default_main_timer_seconds": 1800,
        "default_phase_timer_seconds": 300,
        "rules": {
            "team_mode": True,
            "scoring": "rounds_won",
            "respawn": False,
            "props_used": ["bomb", "respawn_station", "alarm"],
        },
    },
]


def initialize_game_modes(db: Session) -> dict:
    """
    Initialize default game modes in the database.
    
    Returns:
        Dictionary with counts: {"created": int, "existing": int, "total": int}
    """
    created = 0
    existing = 0
    total = 0
    
    for mode_data in DEFAULT_GAME_MODES:
        # Check if game mode already exists
        existing_mode = db.query(GameMode).filter_by(name=mode_data["name"]).first()
        
        if existing_mode:
            existing += 1
        else:
            # Create new game mode
            import json
            new_mode = GameMode(
                name=mode_data["name"],
                description=mode_data["description"],
                default_main_timer_seconds=mode_data["default_main_timer_seconds"],
                default_phase_timer_seconds=mode_data["default_phase_timer_seconds"],
                rules=json.dumps(mode_data["rules"]),
            )
            db.add(new_mode)
            created += 1
        
        total += 1
    
    if created > 0:
        db.commit()
    
    return {
        "created": created,
        "existing": existing,
        "total": total,
    }


def get_game_mode_by_name(db: Session, name: str) -> GameMode | None:
    """Retrieve a game mode by name."""
    return db.query(GameMode).filter_by(name=name).first()


def get_all_game_modes(db: Session) -> list[GameMode]:
    """Retrieve all game modes."""
    return db.query(GameMode).order_by(GameMode.name).all()


def delete_game_mode(db: Session, game_mode_id: int) -> bool:
    """Delete a game mode by ID."""
    mode = db.query(GameMode).filter_by(id=game_mode_id).first()
    if mode:
        db.delete(mode)
        db.commit()
        return True
    return False
