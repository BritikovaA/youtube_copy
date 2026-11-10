from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoListItem(VideoResponse):
    owner: VideoAuthorResponse


class VideoDetailResponse(VideoListItem):
    video_url: str


class VideoUploadResponse(BaseModel):
    video: VideoResponse


class VideoLikeResponse(BaseModel):
    liked: bool
    likes_count: int