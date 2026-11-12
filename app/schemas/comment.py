from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Comment text cannot be empty")

        return normalized


class CommentAuthorResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class CommentResponse(BaseModel):
    id: int
    video_id: int
    user_id: int
    text: str
    created_at: datetime
    author: CommentAuthorResponse