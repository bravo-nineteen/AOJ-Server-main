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
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schedule_columns()


def _ensure_schedule_columns() -> None:
    required_columns = {
        "activity_type": "TEXT NOT NULL DEFAULT 'Custom'",
        "start_time": "DATETIME",
        "end_time": "DATETIME",
        "is_complete": "BOOLEAN NOT NULL DEFAULT 0",
        "completed_at": "DATETIME",
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
