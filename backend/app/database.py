from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL = f"sqlite:///{BASE_DIR / 'aoj_command_os.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models  # noqa: F401 – ensures all ORM classes are registered with Base

    Base.metadata.create_all(bind=engine)
    _ensure_schedule_columns()
    _ensure_system_log_columns()
    _ensure_mission_columns()
    _ensure_game_session_columns()
    _ensure_device_columns()
    _ensure_ai_columns()


def _ensure_schedule_columns() -> None:
    required_columns = {
        "activity_type": "TEXT NOT NULL DEFAULT 'Custom'",
        "start_time": "DATETIME",
        "end_time": "DATETIME",
        "is_complete": "BOOLEAN NOT NULL DEFAULT 0",
        "completed_at": "DATETIME",
        "game_session_id": "INTEGER",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(schedule_items)"))
        existing = {row[1] for row in rows}
        for column_name, column_sql in required_columns.items():
            if column_name in existing:
                continue
            connection.execute(
                text(
                    f"ALTER TABLE schedule_items ADD COLUMN {column_name} {column_sql}"
                )
            )

        connection.execute(
            text(
                "UPDATE schedule_items "
                "SET start_time = COALESCE(start_time, scheduled_for), "
                "end_time = COALESCE(end_time, scheduled_for)"
            )
        )

        if "created_at" not in existing:
            connection.execute(
                text("UPDATE schedule_items SET created_at = COALESCE(created_at, start_time)")
            )

        if "updated_at" not in existing:
            connection.execute(
                text("UPDATE schedule_items SET updated_at = COALESCE(updated_at, created_at)")
            )


def _ensure_system_log_columns() -> None:
    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(system_logs)"))
        existing = {row[1] for row in rows}

        if "category" not in existing:
            connection.execute(
                text(
                    "ALTER TABLE system_logs ADD COLUMN category TEXT NOT NULL DEFAULT 'SYSTEM'"
                )
            )

        if "mission_id" not in existing:
            connection.execute(text("ALTER TABLE system_logs ADD COLUMN mission_id INTEGER"))
        if "game_session_id" not in existing:
            connection.execute(text("ALTER TABLE system_logs ADD COLUMN game_session_id INTEGER"))
        if "device_id" not in existing:
            connection.execute(text("ALTER TABLE system_logs ADD COLUMN device_id INTEGER"))
        if "user_id" not in existing:
            connection.execute(text("ALTER TABLE system_logs ADD COLUMN user_id INTEGER"))

        connection.execute(
            text(
                "UPDATE system_logs SET level = CASE "
                "WHEN level = 'info' THEN 'INFO' "
                "WHEN level = 'warning' THEN 'WARNING' "
                "WHEN level = 'error' THEN 'ERROR' "
                "WHEN level IS NULL OR level = '' THEN 'INFO' "
                "ELSE level END"
            )
        )


def _ensure_ai_columns() -> None:
    ai_message_required_columns = {
        "confidence": "REAL NOT NULL DEFAULT 0.0",
        "used_context": "TEXT NOT NULL DEFAULT '[]'",
        "suggested_actions": "TEXT NOT NULL DEFAULT '[]'",
        "blocked_actions": "TEXT NOT NULL DEFAULT '[]'",
        "warnings": "TEXT NOT NULL DEFAULT '[]'",
        "action_request_id": "INTEGER",
        "updated_at": "DATETIME",
    }
    ai_conversation_required_columns = {
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "memory_summary": "TEXT NOT NULL DEFAULT ''",
        "learned_trends": "TEXT NOT NULL DEFAULT '[]'",
    }

    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            )
        }

        if "ai_messages" in tables:
            rows = connection.execute(text("PRAGMA table_info(ai_messages)"))
            existing = {row[1] for row in rows}
            for column_name, column_sql in ai_message_required_columns.items():
                if column_name in existing:
                    continue
                connection.execute(
                    text(f"ALTER TABLE ai_messages ADD COLUMN {column_name} {column_sql}")
                )
            if "updated_at" not in existing:
                connection.execute(
                    text(
                        "UPDATE ai_messages SET updated_at = COALESCE(updated_at, created_at)"
                    )
                )

        if "ai_conversations" in tables:
            rows = connection.execute(text("PRAGMA table_info(ai_conversations)"))
            existing = {row[1] for row in rows}
            for column_name, column_sql in ai_conversation_required_columns.items():
                if column_name in existing:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE ai_conversations ADD COLUMN {column_name} {column_sql}"
                    )
                )


def _ensure_mission_columns() -> None:
    required_columns = {
        "game_mode_id": "INTEGER",
        "created_by_id": "INTEGER",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(missions)"))
        existing = {row[1] for row in rows}
        for column_name, column_sql in required_columns.items():
            if column_name in existing:
                continue
            connection.execute(
                text(f"ALTER TABLE missions ADD COLUMN {column_name} {column_sql}")
            )

        if "updated_at" not in existing:
            connection.execute(
                text("UPDATE missions SET updated_at = COALESCE(updated_at, created_at)")
            )


def _ensure_game_session_columns() -> None:
    required_columns = {
        "game_mode_id": "INTEGER",
        "main_timer_seconds": "INTEGER NOT NULL DEFAULT 1800",
        "phase_timer_seconds": "INTEGER NOT NULL DEFAULT 300",
        "red_score": "INTEGER NOT NULL DEFAULT 0",
        "blue_score": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(game_sessions)"))
        existing = {row[1] for row in rows}
        for column_name, column_sql in required_columns.items():
            if column_name in existing:
                continue
            connection.execute(
                text(f"ALTER TABLE game_sessions ADD COLUMN {column_name} {column_sql}")
            )

        if "created_at" not in existing:
            connection.execute(
                text("UPDATE game_sessions SET created_at = COALESCE(created_at, start_time)")
            )

        if "updated_at" not in existing:
            connection.execute(
                text("UPDATE game_sessions SET updated_at = COALESCE(updated_at, created_at)")
            )


def _ensure_device_columns() -> None:
    required_columns = {
        "device_id": "TEXT",
        "device_type_id": "INTEGER",
        "battery_level": "INTEGER NOT NULL DEFAULT 100",
        "signal_strength": "INTEGER NOT NULL DEFAULT 100",
        "firmware_version": "TEXT NOT NULL DEFAULT ''",
        "location": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(devices)"))
        existing = {row[1] for row in rows}
        for column_name, column_sql in required_columns.items():
            if column_name in existing:
                continue
            connection.execute(
                text(f"ALTER TABLE devices ADD COLUMN {column_name} {column_sql}")
            )

        if "device_id" not in existing:
            connection.execute(
                text(
                    "UPDATE devices "
                    "SET device_id = COALESCE(NULLIF(device_id, ''), printf('DEV%03d', id))"
                )
            )

        if "updated_at" not in existing:
            connection.execute(
                text("UPDATE devices SET updated_at = COALESCE(updated_at, created_at)")
            )
