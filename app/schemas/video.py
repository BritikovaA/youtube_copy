
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VideoAuthorResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class VideoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    views_count: int
    is_private: bool
    is_hidden: bool
    is_reported: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoListItem(VideoResponse):
    owner: VideoAuthorResponse


class VideoDetailResponse(VideoListItem):
    video_url: str
    likes_count: int


class VideoModerationQueueItem(VideoListItem):
    video_url: str = Field(
        description="Временная ссылка для просмотра видео модератором",
    )


class VideoUploadResponse(BaseModel):
    video: VideoResponse


class VideoLikeResponse(BaseModel):
    liked: bool
    likes_count: int


class VideoModerationRequest(BaseModel):
    is_hidden: bool


class VideoModerationResponse(BaseModel):
    video_id: int
    is_hidden: bool
    is_reported: bool


class VideoReportResponse(BaseModel):
    video_id: int
    is_reported: bool
    message: str
