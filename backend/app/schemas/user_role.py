from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRoleBase(BaseModel):
    role_name: str
    permissions: str = "[]"
    is_active: bool = True


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleRead(UserRoleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
