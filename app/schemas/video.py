from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    file_path: str
    owner_id: int
    views_count: int
    created_at: datetime


class VideoUploadResponse(BaseModel):
    video: VideoResponse
    message: str = "Video uploaded successfully"