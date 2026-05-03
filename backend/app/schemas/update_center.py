from pydantic import BaseModel


class UpdateCenterStatusResponse(BaseModel):
    system_version: str
    frontend_version: str
    backend_version: str
    database_version: str
    database_path: str
    latest_backup: str | None = None
    firmware_packages_count: int = 0
    last_firmware_rollout: str | None = None
    changelog: list[str]


class UpdateCenterActionResponse(BaseModel):
    status: str
    message: str
    placeholder: bool


class UpdatePackagePlaceholderRequest(BaseModel):
    filename: str
    size_bytes: int = 0


class FirmwarePackageRead(BaseModel):
    id: str
    filename: str
    version: str
    size_bytes: int
    sha256: str
    uploaded_at: str
    notes: str = ""


class FirmwareApplyRequest(BaseModel):
    package_id: str
    prop_ids: list[int] = []
    apply_all: bool = False


class FirmwareApplyResponse(BaseModel):
    status: str
    message: str
    package: FirmwarePackageRead
    targeted_props: list[int]
    targeted_count: int
