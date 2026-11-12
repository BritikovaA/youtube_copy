from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.user import Subscription, User
from app.models.video import Video
from app.schemas.user import (
    SubscribedChannelResponse,
    SubscriptionResponse,
    UserResponse,
)
from app.schemas.video import VideoListItem


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser,
) -> User:
    return current_user


@router.get(
    "/subscriptions",
    response_model=list[SubscribedChannelResponse],
)
async def get_subscriptions(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> list[User]:
    result = await db.execute(
        select(User)
        .join(
            Subscription,
            Subscription.channel_id == User.id,
        )
        .where(
            Subscription.subscriber_id == current_user.id,
        )
        .order_by(User.created_at.desc()),
    )

    return list(result.scalars().all())


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    db: DatabaseSession,
) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id),
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get(
    "/{user_id}/subscription",
    response_model=SubscriptionResponse,
)
async def get_subscription_status(
    user_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> SubscriptionResponse:
    result = await db.execute(
        select(User).where(User.id == user_id),
    )
    channel = result.scalar_one_or_none()

    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    subscribers_result = await db.execute(
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.channel_id == user_id),
    )
    subscribers_count = subscribers_result.scalar_one()

    if current_user.id == user_id:
        return SubscriptionResponse(
            subscribed=False,
            subscribers_count=subscribers_count,
        )

    subscription_result = await db.execute(
        select(Subscription).where(
            Subscription.subscriber_id == current_user.id,
            Subscription.channel_id == user_id,
        ),
    )

    return SubscriptionResponse(
        subscribed=subscription_result.scalar_one_or_none() is not None,
        subscribers_count=subscribers_count,
    )


@router.get(
    "/me/videos",
    response_model=list[VideoListItem],
)
async def get_my_videos(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> list[Video]:
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(
            Video.owner_id == current_user.id,
        )
        .order_by(Video.created_at.desc()),
    )

    return list(result.scalars().unique().all())


@router.get(
    "/{user_id}/videos",
    response_model=list[VideoListItem],
)
async def get_user_videos(
    user_id: int,
    db: DatabaseSession,
) -> list[Video]:
    user_result = await db.execute(
        select(User).where(User.id == user_id),
    )

    if user_result.scalar_one_or_none() is None:
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
            Video.is_hidden.is_(False),
        )
        .order_by(Video.created_at.desc()),
    )

    return list(result.scalars().unique().all())


@router.post(
    "/{user_id}/subscribe",
    response_model=SubscriptionResponse,
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

    channel_result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .with_for_update(),
    )
    channel = channel_result.scalar_one_or_none()

    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    subscription_result = await db.execute(
        select(Subscription).where(
            Subscription.subscriber_id == current_user.id,
            Subscription.channel_id == user_id,
        ),
    )
    subscription = subscription_result.scalar_one_or_none()

    if subscription is None:
        db.add(
            Subscription(
                subscriber_id=current_user.id,
                channel_id=user_id,
            ),
        )
        subscribed = True
    else:
        await db.delete(subscription)
        subscribed = False

    await db.flush()

    count_result = await db.execute(
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.channel_id == user_id),
    )
    subscribers_count = count_result.scalar_one()

    await db.commit()

    return SubscriptionResponse(
        subscribed=subscribed,
        subscribers_count=subscribers_count,
    )