import csv
import io

from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/logs", tags=["Logs"])


@router.get("", response_model=list[schemas.SystemLogRead])
def list_logs(
    level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.SystemLog)
    if level:
        try:
            query = query.filter(models.SystemLog.level == models.LogLevel(level.upper()))
        except ValueError:
            return []
    if category:
        try:
            query = query.filter(
                models.SystemLog.category == models.LogCategory(category.upper())
            )
        except ValueError:
            return []
    return query.order_by(models.SystemLog.id.desc()).all()


@router.delete("")
def clear_logs(db: Session = Depends(get_db)):
    count = db.query(models.SystemLog).delete()
    db.commit()
    return {"status": "cleared", "deleted": count}


@router.get("/export/csv")
def export_logs_csv(
    level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.SystemLog)
    if level:
        try:
            query = query.filter(models.SystemLog.level == models.LogLevel(level.upper()))
        except ValueError:
            rows = []
            return _csv_response(rows)
    if category:
        try:
            query = query.filter(
                models.SystemLog.category == models.LogCategory(category.upper())
            )
        except ValueError:
            rows = []
            return _csv_response(rows)

    rows = query.order_by(models.SystemLog.id.desc()).all()

    return _csv_response(rows)


def _csv_response(rows: list[models.SystemLog]):

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "level", "category", "source", "message", "created_at"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.level.value,
                row.category.value,
                row.source,
                row.message,
                row.created_at.isoformat(),
            ]
        )

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=aoj_system_logs.csv"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)
