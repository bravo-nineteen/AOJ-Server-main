from pydantic import BaseModel


class UpdateCenterStatusResponse(BaseModel):
    system_version: str
    frontend_version: str
    backend_version: str
    database_version: str
    database_path: str
    latest_backup: str | None = None
    changelog: list[str]


class UpdateCenterActionResponse(BaseModel):
    status: str
    message: str
    placeholder: bool


class UpdatePackagePlaceholderRequest(BaseModel):
    filename: str
    size_bytes: int = 0
