"""
Device Initialization Service

Seeds the database with all built-in AOJ firmware devices.
"""

from sqlalchemy.orm import Session

from app import models


DEFAULT_DEVICES = [
    # Bomb Props
    {
        "device_id": "BD-001",
        "name": "Main Bomb",
        "prop_type": "Bomb",
        "location": "Arena Center",
        "firmware_version": "1.3.8",
    },
    {
        "device_id": "VEST-001",
        "name": "Bomb Vest",
        "prop_type": "Bomb Vest",
        "location": "Player Loadout Area",
        "firmware_version": "1.2.0",
    },
    {
        "device_id": "CASE-001",
        "name": "Briefcase Bomb",
        "prop_type": "Briefcase Bomb",
        "location": "Mission Control",
        "firmware_version": "1.1.0",
    },
    # Domination Points
    {
        "device_id": "DOM-001",
        "name": "Domination Point A",
        "prop_type": "Domination Point",
        "location": "Arena North",
        "firmware_version": "1.0.0",
    },
    {
        "device_id": "DOM-002",
        "name": "Domination Point B",
        "prop_type": "Domination Point",
        "location": "Arena South",
        "firmware_version": "1.0.0",
    },
    # Respawn Stations
    {
        "device_id": "RESP-001",
        "name": "Respawn Station - Team Alpha",
        "prop_type": "Respawn Station",
        "location": "Team Alpha Spawn Zone",
        "firmware_version": "1.0.0",
    },
    {
        "device_id": "RESP-002",
        "name": "Respawn Station - Team Bravo",
        "prop_type": "Respawn Station",
        "location": "Team Bravo Spawn Zone",
        "firmware_version": "1.0.0",
    },
    # Control Units
    {
        "device_id": "GM-001",
        "name": "Game Master Unit",
        "prop_type": "Game Master Unit",
        "location": "Control Room",
        "firmware_version": "1.0.0",
    },
    {
        "device_id": "CP-001",
        "name": "Control Panel Unit",
        "prop_type": "Control Panel Unit",
        "location": "Mission Control Center",
        "firmware_version": "1.0.0",
    },
]


def initialize_devices(db: Session) -> dict[str, int]:
    """
    Seed the database with all default devices.

    Returns:
        Dictionary with counts of created and existing devices.
    """
    created_count = 0
    existing_count = 0

    for device_data in DEFAULT_DEVICES:
        existing = db.query(models.Prop).filter(
            models.Prop.device_id == device_data["device_id"]
        ).first()

        if existing:
            existing_count += 1
            # Update existing device if needed
            if existing.firmware_version != device_data.get("firmware_version"):
                existing.firmware_version = device_data["firmware_version"]
                db.commit()
        else:
            new_device = models.Prop(
                **device_data,
                status="offline",  # Devices start as offline
            )
            db.add(new_device)
            created_count += 1

    db.commit()

    return {
        "created": created_count,
        "existing": existing_count,
        "total": len(DEFAULT_DEVICES),
    }


def get_device_by_id(db: Session, device_id: str) -> models.Prop | None:
    """Get a device by its device_id."""
    return db.query(models.Prop).filter(models.Prop.device_id == device_id).first()


def get_devices_by_type(db: Session, prop_type: str) -> list[models.Prop]:
    """Get all devices of a specific type."""
    return db.query(models.Prop).filter(models.Prop.prop_type == prop_type).all()


def get_offline_devices(db: Session) -> list[models.Prop]:
    """Get all offline devices."""
    return db.query(models.Prop).filter(models.Prop.status == "offline").all()


def get_low_battery_devices(db: Session, threshold: int = 20) -> list[models.Prop]:
    """Get all devices with battery below threshold."""
    return db.query(models.Prop).filter(models.Prop.battery_level < threshold).all()


def get_weak_signal_devices(db: Session, threshold: int = 30) -> list[models.Prop]:
    """Get all devices with weak signal below threshold."""
    return db.query(models.Prop).filter(models.Prop.signal_strength < threshold).all()


def get_device_stats(db: Session) -> dict:
    """Get comprehensive statistics about all devices."""
    props = db.query(models.Prop).all()

    if not props:
        return {
            "total_devices": 0,
            "status_counts": {},
            "type_counts": {},
            "battery_average": 0,
            "signal_average": 0,
        }

    status_counts = {}
    type_counts = {}
    total_battery = 0
    total_signal = 0

    for prop in props:
        # Count by status
        status_counts[prop.status] = status_counts.get(prop.status, 0) + 1

        # Count by type
        type_counts[prop.prop_type] = type_counts.get(prop.prop_type, 0) + 1

        # Accumulate battery and signal
        total_battery += prop.battery_level
        total_signal += prop.signal_strength

    return {
        "total_devices": len(props),
        "status_counts": status_counts,
        "type_counts": type_counts,
        "battery_average": round(total_battery / len(props), 1),
        "signal_average": round(total_signal / len(props), 1),
        "offline_devices": status_counts.get("offline", 0),
        "low_battery_devices": len(get_low_battery_devices(db)),
        "weak_signal_devices": len(get_weak_signal_devices(db)),
    }
