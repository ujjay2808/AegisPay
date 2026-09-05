from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import NonBlankText, SpendingConstraints


class IntentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: NonBlankText = Field(min_length=1, max_length=128)
    user_id: NonBlankText = Field(min_length=1, max_length=128)
    purpose: NonBlankText = Field(min_length=1, max_length=500)
    spending_constraints: SpendingConstraints | None = None


class IntentCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: NonBlankText = Field(min_length=1, max_length=128)
    agent_id: NonBlankText = Field(min_length=1, max_length=128)
    user_id: NonBlankText = Field(min_length=1, max_length=128)
    status: str = Field(min_length=1, max_length=32)
