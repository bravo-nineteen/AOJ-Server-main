from pydantic import BaseModel, Field


class AIAskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class AIAskResponse(BaseModel):
    answer: str
    advisory_only: bool = True
    requires_admin_confirmation: bool = False
    blocked_action: bool = False
    safety_notice: str
    model: str
