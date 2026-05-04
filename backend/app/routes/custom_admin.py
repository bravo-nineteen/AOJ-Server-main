import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Custom Admin"])
TEAM_LOGO_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads" / "team-logos"


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _write_log(
    db: Session,
    *,
    level: models.LogLevel,
    category: models.LogCategory,
    source: str,
    message: str,
) -> None:
    try:
        row = models.SystemLog(
            level=level,
            category=category,
            source=source,
            message=message,
        )
        db.add(row)
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def _serialize_game_mode(item: models.CustomGameMode) -> schemas.CustomGameModeRead:
    try:
        team_setup = json.loads(item.team_setup_json) if item.team_setup_json else {}
        if not isinstance(team_setup, dict):
            team_setup = {}
    except json.JSONDecodeError:
        team_setup = {}

    try:
        objectives = json.loads(item.objectives_json) if item.objectives_json else []
        if not isinstance(objectives, list):
            objectives = []
    except json.JSONDecodeError:
        objectives = []

    try:
        scoring = json.loads(item.scoring_rules_json) if item.scoring_rules_json else {}
        if not isinstance(scoring, dict):
            scoring = {}
    except json.JSONDecodeError:
        scoring = {}

    try:
        objective = json.loads(item.objective_rules_json) if item.objective_rules_json else {}
        if not isinstance(objective, dict):
            objective = {}
    except json.JSONDecodeError:
        objective = {}

    try:
        win_conditions = json.loads(item.win_conditions_json) if item.win_conditions_json else []
        if not isinstance(win_conditions, list):
            win_conditions = []
    except json.JSONDecodeError:
        win_conditions = []

    try:
        required_props = json.loads(item.required_props_json) if item.required_props_json else []
        if not isinstance(required_props, list):
            required_props = []
    except json.JSONDecodeError:
        required_props = []

    return schemas.CustomGameModeRead(
        id=item.id,
        name=item.name,
        category=item.category,
        description=item.description,
        rules_text=item.rules_text,
        default_duration_minutes=item.default_duration_minutes,
        team_setup_json=team_setup,
        objectives_json=[str(obj) for obj in objectives if str(obj).strip()],
        scoring_rules_json=scoring,
        objective_rules_json=objective,
        respawn_rules_text=item.respawn_rules_text,
        win_conditions_json=[str(item) for item in win_conditions if str(item).strip()],
        required_props_json=[str(item) for item in required_props if str(item).strip()],
        briefing_text=item.briefing_text,
        marshal_notes=item.marshal_notes,
        active=item.active,
    )


def _serialize_knowledge(item: models.CustomKnowledgeEntry) -> schemas.CustomKnowledgeEntryRead:
    try:
        tags = json.loads(item.tags) if item.tags else []
        if not isinstance(tags, list):
            tags = []
    except json.JSONDecodeError:
        tags = []

    tags_clean = [str(tag) for tag in tags if str(tag).strip()]
    return schemas.CustomKnowledgeEntryRead(
        id=item.id,
        title=item.title,
        category=item.category,
        content=item.content,
        tags=tags_clean,
        active=item.active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/custom/teams", response_model=list[schemas.CustomTeamRead])
def list_custom_teams(db: Session = Depends(get_db)) -> list[models.CustomTeam]:
    rows = db.query(models.CustomTeam).order_by(models.CustomTeam.id.desc()).all()
    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Listed custom teams ({len(rows)} records)",
    )
    return rows


@router.post("/custom/teams", response_model=schemas.CustomTeamRead)
def create_custom_team(payload: schemas.CustomTeamCreate, db: Session = Depends(get_db)) -> models.CustomTeam:
    item = models.CustomTeam(**payload.model_dump())
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "TEAM_CREATE_FAILED", "Failed to create custom team.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Created custom team id={item.id} name={item.name}",
    )
    return item


@router.post("/custom/teams/logo-upload")
async def upload_custom_team_logo(file: UploadFile = File(...)) -> dict[str, str]:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise _error(400, "INVALID_FILE_TYPE", "Only image files are allowed.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        suffix = ".png"

    TEAM_LOGO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"team_logo_{uuid.uuid4().hex}{suffix}"
    destination = TEAM_LOGO_DIR / filename
    payload = await file.read()
    if not payload:
        raise _error(400, "EMPTY_FILE", "Uploaded file is empty.")

    destination.write_bytes(payload)
    return {"url": f"/uploads/team-logos/{filename}"}


@router.put("/custom/teams/{team_id}", response_model=schemas.CustomTeamRead)
def update_custom_team(
    team_id: int,
    payload: schemas.CustomTeamUpdate,
    db: Session = Depends(get_db),
) -> models.CustomTeam:
    item = db.query(models.CustomTeam).filter(models.CustomTeam.id == team_id).first()
    if item is None:
        raise _error(404, "TEAM_NOT_FOUND", "Custom team not found.")

    for key, value in payload.model_dump().items():
        setattr(item, key, value)

    try:
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "TEAM_UPDATE_FAILED", "Failed to update custom team.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Updated custom team id={item.id}",
    )
    return item


@router.delete("/custom/teams/{team_id}")
def delete_custom_team(team_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.query(models.CustomTeam).filter(models.CustomTeam.id == team_id).first()
    if item is None:
        raise _error(404, "TEAM_NOT_FOUND", "Custom team not found.")

    try:
        db.delete(item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "TEAM_DELETE_FAILED", "Failed to delete custom team.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Deleted custom team id={team_id}",
    )
    return {"status": "deleted"}


@router.get("/custom/game-modes", response_model=list[schemas.CustomGameModeRead])
def list_custom_game_modes(db: Session = Depends(get_db)) -> list[schemas.CustomGameModeRead]:
    rows = (
        db.query(models.CustomGameMode)
        .order_by(models.CustomGameMode.id.desc())
        .all()
    )
    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Listed custom game modes ({len(rows)} records)",
    )
    return [_serialize_game_mode(row) for row in rows]


@router.post("/custom/game-modes", response_model=schemas.CustomGameModeRead)
def create_custom_game_mode(
    payload: schemas.CustomGameModeCreate,
    db: Session = Depends(get_db),
) -> schemas.CustomGameModeRead:
    item = models.CustomGameMode(
        **{
            **payload.model_dump(
                exclude={
                    "team_setup_json",
                    "objectives_json",
                    "scoring_rules_json",
                    "objective_rules_json",
                    "win_conditions_json",
                    "required_props_json",
                }
            ),
            "team_setup_json": json.dumps(payload.team_setup_json, ensure_ascii=True),
            "objectives_json": json.dumps(payload.objectives_json, ensure_ascii=True),
            "scoring_rules_json": json.dumps(payload.scoring_rules_json, ensure_ascii=True),
            "objective_rules_json": json.dumps(payload.objective_rules_json, ensure_ascii=True),
            "win_conditions_json": json.dumps(payload.win_conditions_json, ensure_ascii=True),
            "required_props_json": json.dumps(payload.required_props_json, ensure_ascii=True),
        }
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "GAME_MODE_CREATE_FAILED", "Failed to create custom game mode.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Created custom game mode id={item.id} name={item.name}",
    )
    return _serialize_game_mode(item)


@router.put("/custom/game-modes/{game_mode_id}", response_model=schemas.CustomGameModeRead)
def update_custom_game_mode(
    game_mode_id: int,
    payload: schemas.CustomGameModeUpdate,
    db: Session = Depends(get_db),
) -> schemas.CustomGameModeRead:
    item = (
        db.query(models.CustomGameMode)
        .filter(models.CustomGameMode.id == game_mode_id)
        .first()
    )
    if item is None:
        raise _error(404, "GAME_MODE_NOT_FOUND", "Custom game mode not found.")

    item_data = payload.model_dump(
        exclude={
            "team_setup_json",
            "objectives_json",
            "scoring_rules_json",
            "objective_rules_json",
            "win_conditions_json",
            "required_props_json",
        }
    )
    for key, value in item_data.items():
        setattr(item, key, value)
    item.team_setup_json = json.dumps(payload.team_setup_json, ensure_ascii=True)
    item.objectives_json = json.dumps(payload.objectives_json, ensure_ascii=True)
    item.scoring_rules_json = json.dumps(payload.scoring_rules_json, ensure_ascii=True)
    item.objective_rules_json = json.dumps(payload.objective_rules_json, ensure_ascii=True)
    item.win_conditions_json = json.dumps(payload.win_conditions_json, ensure_ascii=True)
    item.required_props_json = json.dumps(payload.required_props_json, ensure_ascii=True)

    try:
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "GAME_MODE_UPDATE_FAILED", "Failed to update custom game mode.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Updated custom game mode id={item.id}",
    )
    return _serialize_game_mode(item)


@router.delete("/custom/game-modes/{game_mode_id}")
def delete_custom_game_mode(game_mode_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = (
        db.query(models.CustomGameMode)
        .filter(models.CustomGameMode.id == game_mode_id)
        .first()
    )
    if item is None:
        raise _error(404, "GAME_MODE_NOT_FOUND", "Custom game mode not found.")

    try:
        db.delete(item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "GAME_MODE_DELETE_FAILED", "Failed to delete custom game mode.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Deleted custom game mode id={game_mode_id}",
    )
    return {"status": "deleted"}


@router.get("/custom/knowledge", response_model=list[schemas.CustomKnowledgeEntryRead])
def list_custom_knowledge(db: Session = Depends(get_db)) -> list[schemas.CustomKnowledgeEntryRead]:
    rows = (
        db.query(models.CustomKnowledgeEntry)
        .order_by(models.CustomKnowledgeEntry.updated_at.desc(), models.CustomKnowledgeEntry.id.desc())
        .all()
    )
    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Listed custom knowledge entries ({len(rows)} records)",
    )
    return [_serialize_knowledge(row) for row in rows]


@router.post("/custom/knowledge", response_model=schemas.CustomKnowledgeEntryRead)
def create_custom_knowledge(
    payload: schemas.CustomKnowledgeEntryCreate,
    db: Session = Depends(get_db),
) -> schemas.CustomKnowledgeEntryRead:
    item = models.CustomKnowledgeEntry(
        **{
            **payload.model_dump(exclude={"tags"}),
            "tags": json.dumps(payload.tags, ensure_ascii=True),
        }
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "KNOWLEDGE_CREATE_FAILED", "Failed to create custom knowledge entry.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Created custom knowledge entry id={item.id} title={item.title}",
    )
    return _serialize_knowledge(item)


@router.put("/custom/knowledge/{entry_id}", response_model=schemas.CustomKnowledgeEntryRead)
def update_custom_knowledge(
    entry_id: int,
    payload: schemas.CustomKnowledgeEntryUpdate,
    db: Session = Depends(get_db),
) -> schemas.CustomKnowledgeEntryRead:
    item = (
        db.query(models.CustomKnowledgeEntry)
        .filter(models.CustomKnowledgeEntry.id == entry_id)
        .first()
    )
    if item is None:
        raise _error(404, "KNOWLEDGE_NOT_FOUND", "Custom knowledge entry not found.")

    item_data = payload.model_dump(exclude={"tags"})
    for key, value in item_data.items():
        setattr(item, key, value)
    item.tags = json.dumps(payload.tags, ensure_ascii=True)

    try:
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "KNOWLEDGE_UPDATE_FAILED", "Failed to update custom knowledge entry.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Updated custom knowledge entry id={item.id}",
    )
    return _serialize_knowledge(item)


@router.delete("/custom/knowledge/{entry_id}")
def delete_custom_knowledge(entry_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = (
        db.query(models.CustomKnowledgeEntry)
        .filter(models.CustomKnowledgeEntry.id == entry_id)
        .first()
    )
    if item is None:
        raise _error(404, "KNOWLEDGE_NOT_FOUND", "Custom knowledge entry not found.")

    try:
        db.delete(item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "KNOWLEDGE_DELETE_FAILED", "Failed to delete custom knowledge entry.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Deleted custom knowledge entry id={entry_id}",
    )
    return {"status": "deleted"}


@router.get("/custom/themes", response_model=list[schemas.VisualThemeRead])
def list_visual_themes(db: Session = Depends(get_db)) -> list[models.VisualTheme]:
    rows = db.query(models.VisualTheme).order_by(models.VisualTheme.id.desc()).all()
    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Listed visual themes ({len(rows)} records)",
    )
    return rows


@router.post("/custom/themes", response_model=schemas.VisualThemeRead)
def create_visual_theme(payload: schemas.VisualThemeCreate, db: Session = Depends(get_db)) -> models.VisualTheme:
    item = models.VisualTheme(**payload.model_dump())

    try:
        db.add(item)
        if payload.is_active:
            db.query(models.VisualTheme).filter(models.VisualTheme.id != item.id).update(
                {models.VisualTheme.is_active: False}, synchronize_session=False
            )
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "THEME_CREATE_FAILED", "Failed to create visual theme.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Created visual theme id={item.id} name={item.name}",
    )
    return item


@router.put("/custom/themes/{theme_id}", response_model=schemas.VisualThemeRead)
def update_visual_theme(
    theme_id: int,
    payload: schemas.VisualThemeUpdate,
    db: Session = Depends(get_db),
) -> models.VisualTheme:
    item = db.query(models.VisualTheme).filter(models.VisualTheme.id == theme_id).first()
    if item is None:
        raise _error(404, "THEME_NOT_FOUND", "Visual theme not found.")

    for key, value in payload.model_dump().items():
        setattr(item, key, value)

    try:
        if payload.is_active:
            db.query(models.VisualTheme).filter(models.VisualTheme.id != theme_id).update(
                {models.VisualTheme.is_active: False}, synchronize_session=False
            )
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "THEME_UPDATE_FAILED", "Failed to update visual theme.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Updated visual theme id={item.id}",
    )
    return item


@router.delete("/custom/themes/{theme_id}")
def delete_visual_theme(theme_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.query(models.VisualTheme).filter(models.VisualTheme.id == theme_id).first()
    if item is None:
        raise _error(404, "THEME_NOT_FOUND", "Visual theme not found.")

    try:
        db.delete(item)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "THEME_DELETE_FAILED", "Failed to delete visual theme.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Deleted visual theme id={theme_id}",
    )
    return {"status": "deleted"}


@router.get("/custom/themes/active", response_model=schemas.VisualThemeRead)
def get_active_visual_theme(db: Session = Depends(get_db)) -> models.VisualTheme:
    item = db.query(models.VisualTheme).filter(models.VisualTheme.is_active.is_(True)).first()
    if item is None:
        raise _error(404, "ACTIVE_THEME_NOT_FOUND", "No active visual theme configured.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Read active visual theme id={item.id}",
    )
    return item


@router.post("/custom/themes/active", response_model=schemas.VisualThemeRead)
def set_active_visual_theme(
    payload: schemas.ActiveThemeSetRequest,
    db: Session = Depends(get_db),
) -> models.VisualTheme:
    item = db.query(models.VisualTheme).filter(models.VisualTheme.id == payload.theme_id).first()
    if item is None:
        raise _error(404, "THEME_NOT_FOUND", "Visual theme not found.")

    try:
        db.query(models.VisualTheme).update(
            {models.VisualTheme.is_active: False}, synchronize_session=False
        )
        item.is_active = True
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "ACTIVE_THEME_SET_FAILED", "Failed to set active visual theme.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.system,
        source="custom_admin",
        message=f"Set active visual theme id={item.id}",
    )
    return item


@router.get("/ai/settings", response_model=schemas.AIAssistantSettingsRead)
def get_ai_settings(db: Session = Depends(get_db)) -> schemas.AIAssistantSettingsRead:
    item = db.query(models.AIAssistantSettings).order_by(models.AIAssistantSettings.id.asc()).first()
    if item is None:
        item = models.AIAssistantSettings()
        try:
            db.add(item)
            db.commit()
            db.refresh(item)
        except SQLAlchemyError:
            db.rollback()
            raise _error(500, "AI_SETTINGS_READ_FAILED", "Failed to initialize AI settings.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Read AI assistant settings id={item.id}",
    )
    return schemas.AIAssistantSettingsRead.model_validate(item)


@router.put("/ai/settings", response_model=schemas.AIAssistantSettingsRead)
def update_ai_settings(
    payload: schemas.AIAssistantSettingsUpdate,
    db: Session = Depends(get_db),
) -> schemas.AIAssistantSettingsRead:
    item = db.query(models.AIAssistantSettings).order_by(models.AIAssistantSettings.id.asc()).first()
    if item is None:
        item = models.AIAssistantSettings()
        db.add(item)

    for key, value in payload.model_dump().items():
        setattr(item, key, value)

    try:
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise _error(500, "AI_SETTINGS_UPDATE_FAILED", "Failed to update AI settings.")

    _write_log(
        db,
        level=models.LogLevel.info,
        category=models.LogCategory.ai,
        source="custom_admin",
        message=f"Updated AI assistant settings id={item.id}",
    )
    return schemas.AIAssistantSettingsRead.model_validate(item)
