from sqlalchemy.orm import Session

from app import models


def log_action(
    db: Session,
    *,
    level: models.LogLevel,
    category: models.LogCategory,
    source: str,
    message: str,
) -> models.SystemLog:
    item = models.SystemLog(
        level=level,
        category=category,
        source=source,
        message=message,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
