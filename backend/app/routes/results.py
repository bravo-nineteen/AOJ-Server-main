import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app import models, schemas
from app.database import get_db
from app.services.log_service import log_action

router = APIRouter(prefix="/api/results", tags=["Results"])


@router.get("/history", response_model=list[schemas.GameResultRead])
def list_results_history(db: Session = Depends(get_db)):
    return db.query(models.GameResult).order_by(models.GameResult.created_at.desc()).all()


@router.post("", response_model=schemas.GameResultRead)
def record_game_result(payload: schemas.GameResultCreate, db: Session = Depends(get_db)):
    result = models.GameResult(**payload.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    log_action(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.mission,
        source="results",
        message=(
            f"Result recorded: session={result.session_name} winner={result.winner.value} "
            f"red={result.red_points} blue={result.blue_points}"
        ),
    )
    return result


@router.get("/summary", response_model=schemas.ResultsSummaryResponse)
def get_results_summary(db: Session = Depends(get_db)):
    total_red_wins = (
        db.query(func.count(models.GameResult.id))
        .filter(models.GameResult.winner == models.ResultWinner.red)
        .scalar()
        or 0
    )
    total_blue_wins = (
        db.query(func.count(models.GameResult.id))
        .filter(models.GameResult.winner == models.ResultWinner.blue)
        .scalar()
        or 0
    )
    total_draws = (
        db.query(func.count(models.GameResult.id))
        .filter(models.GameResult.winner == models.ResultWinner.draw)
        .scalar()
        or 0
    )
    total_cancelled = (
        db.query(func.count(models.GameResult.id))
        .filter(models.GameResult.winner == models.ResultWinner.cancelled)
        .scalar()
        or 0
    )

    total_red_points = db.query(func.sum(models.GameResult.red_points)).scalar() or 0
    total_blue_points = db.query(func.sum(models.GameResult.blue_points)).scalar() or 0

    return schemas.ResultsSummaryResponse(
        total_red_wins=total_red_wins,
        total_blue_wins=total_blue_wins,
        total_draws=total_draws,
        total_cancelled=total_cancelled,
        total_red_points=total_red_points,
        total_blue_points=total_blue_points,
    )


@router.get("/export/csv")
def export_results_csv(db: Session = Depends(get_db)):
    rows = db.query(models.GameResult).order_by(models.GameResult.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_name",
            "winner",
            "red_points",
            "blue_points",
            "red_penalties",
            "blue_penalties",
            "notes",
            "created_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.session_name,
                row.winner.value,
                row.red_points,
                row.blue_points,
                row.red_penalties,
                row.blue_penalties,
                row.notes,
                row.created_at.isoformat(),
            ]
        )

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=aoj_results_history.csv"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)


@router.post("/reset-day", response_model=schemas.ResultsResetDayResponse)
def reset_results_for_day(
    payload: schemas.ResultsResetDayRequest,
    db: Session = Depends(get_db),
):
    try:
        day_start = datetime.strptime(payload.day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="day must be in YYYY-MM-DD format")

    day_end = day_start + timedelta(days=1)

    deleted_count = (
        db.query(models.GameResult)
        .filter(models.GameResult.created_at >= day_start)
        .filter(models.GameResult.created_at < day_end)
        .delete(synchronize_session=False)
    )
    db.commit()

    log_action(
        db,
        level=models.LogLevel.warning,
        category=models.LogCategory.mission,
        source="results",
        message=f"Results reset for day={payload.day}, deleted={deleted_count}",
    )

    return schemas.ResultsResetDayResponse(day=payload.day, deleted_results=deleted_count)
