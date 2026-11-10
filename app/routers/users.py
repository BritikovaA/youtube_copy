from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.user import Subscription, User
from app.models.video import Video
from app.schemas.user import SubscriptionResponse, UserResponse
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
        .where(
            Video.owner_id == user_id,
            Video.is_private.is_(False),
        )
        .order_by(Video.created_at.desc())
    )

    videos = result.scalars().all()

    return [
        VideoListItem.model_validate(video)
        for video in videos
    ]


@router.post(
    "/{user_id}/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def toggle_subscription(
    user_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> SubscriptionResponse:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot subscribe to your own channel",
        )

    channel = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )

    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing_subscription = await db.scalar(
        select(Subscription).where(
            Subscription.subscriber_id == current_user.id,
            Subscription.channel_id == user_id,
        )
    )

    if existing_subscription is not None:
        await db.delete(existing_subscription)
        subscribed = False
    else:
        db.add(
            Subscription(
                subscriber_id=current_user.id,
                channel_id=user_id,
            )
        )
        subscribed = True

    await db.commit()

    subscribers_count = await db.scalar(
        select(Subscription.id)
        .where(Subscription.channel_id == user_id)
    )

    # Подсчёт количества подписчиков.
    from sqlalchemy import func

    subscribers_count = await db.scalar(
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.channel_id == user_id)
    )

    return SubscriptionResponse(
        subscribed=subscribed,
        subscribers_count=int(subscribers_count or 0),
    )