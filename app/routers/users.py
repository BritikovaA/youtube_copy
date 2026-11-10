from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.user import User
from app.models.video import Video
from app.schemas.user import UserResponse
from app.schemas.video import VideoListItem


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/{user_id}/videos",
    response_model=list[VideoListItem],
    status_code=status.HTTP_200_OK,
)
async def get_user_videos(
    user_id: int,
    db: DatabaseSession,
) -> list[VideoListItem]:
    user_exists = await db.scalar(
        select(User.id).where(User.id == user_id)
    )

    if user_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.owner_id == user_id)
        .order_by(Video.created_at.desc())
    )

    videos = result.scalars().all()

    return [
        VideoListItem.model_validate(video)
        for video in videos
    ]