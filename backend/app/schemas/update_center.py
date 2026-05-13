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
    manifest_sha256: str = ""
    signature: str = ""


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
    rollout_job_id: int


class FirmwareRolloutTargetRead(BaseModel):
    prop_id: int
    device_id: str
    name: str
    status: str
    message: str = ""
    updated_at: str


class FirmwareRolloutJobRead(BaseModel):
    id: int
    package_id: str
    package_version: str
    package_filename: str
    status: str
    targeted_count: int
    acknowledged_count: int
    failed_count: int
    targets: list[FirmwareRolloutTargetRead]
    created_at: str
    updated_at: str


class FirmwareRolloutProgressUpdateRequest(BaseModel):
    prop_id: int
    status: str
    message: str = ""
