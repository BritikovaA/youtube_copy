
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    subscribed: bool
    subscribers_count: int


class SubscribedChannelResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
