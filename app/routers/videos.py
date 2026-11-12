from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import joinedload

from app.core.dependencies import (
    CurrentUser,
    DatabaseSession,
    OptionalCurrentUser,
)
from app.models.user import UserRole
from app.models.video import Video, VideoLike
from app.schemas.video import (
    VideoDetailResponse,
    VideoLikeResponse,
    VideoListItem,
    VideoModerationRequest,
    VideoModerationResponse,
    VideoResponse,
    VideoUploadResponse,
)
from app.services.storage import (
    InvalidVideoError,
    UploadTooLargeError,
    create_video_presigned_url,
    delete_object,
    upload_video,
    validate_video,
)


router = APIRouter(
    prefix="/videos",
    tags=["Videos"],
)


async def get_likes_count(
    db: DatabaseSession,
    video_id: int,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(VideoLike)
        .where(VideoLike.video_id == video_id),
    )

    return result.scalar_one()


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video_endpoint(
    current_user: CurrentUser,
    db: DatabaseSession,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    description: Annotated[str | None, Form()] = None,
    is_private: Annotated[bool, Form()] = False,
) -> VideoUploadResponse:
    try:
        await validate_video(file)

        file_path = await upload_video(file)

        video = Video(
            title=title,
            description=description,
            file_path=file_path,
            owner_id=current_user.id,
            is_private=is_private,
        )

        db.add(video)
        await db.commit()
        await db.refresh(video)

        return VideoUploadResponse(video=video)

    except (InvalidVideoError, UploadTooLargeError):
        raise
    except Exception:
        await db.rollback()

        if "file_path" in locals():
            await delete_object(file_path)

        raise


@router.get(
    "",
    response_model=list[VideoListItem],
)
async def get_videos(
    db: DatabaseSession,
    search: Annotated[str | None, Query()] = None,
) -> list[Video]:
    query = (
        select(Video)
        .options(joinedload(Video.owner))
        .where(
            Video.is_private.is_(False),
            Video.is_hidden.is_(False),
        )
        .order_by(Video.created_at.desc())
    )

    if search:
        query = query.where(Video.title.ilike(f"%{search}%"))

    result = await db.execute(query)

    return list(result.scalars().unique().all())


@router.get(
    "/{video_id}",
    response_model=VideoDetailResponse,
)
async def get_video(
    video_id: int,
    db: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> VideoDetailResponse:
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.id == video_id),
    )
    video = result.scalar_one_or_none()

    if video is None or video.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if (
        video.is_private
        and (
            current_user is None
            or current_user.id != video.owner_id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    await db.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(views_count=Video.views_count + 1),
    )
    await db.commit()
    await db.refresh(video)

    likes_count = await get_likes_count(db, video_id)

    video_url = await create_video_presigned_url(video.file_path)

    return VideoDetailResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        views_count=video.views_count,
        is_private=video.is_private,
        is_hidden=video.is_hidden,
        created_at=video.created_at,
        owner=video.owner,
        video_url=video_url,
        likes_count=likes_count,
    )


@router.get(
    "/{video_id}/like",
    response_model=VideoLikeResponse,
)
async def get_video_like_status(
    video_id: int,
    db: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> VideoLikeResponse:
    video_result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.is_hidden.is_(False),
        ),
    )
    video = video_result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if (
        video.is_private
        and (
            current_user is None
            or current_user.id != video.owner_id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    likes_count = await get_likes_count(db, video_id)

    if current_user is None:
        return VideoLikeResponse(
            liked=False,
            likes_count=likes_count,
        )

    like_result = await db.execute(
        select(VideoLike).where(
            VideoLike.video_id == video_id,
            VideoLike.user_id == current_user.id,
        ),
    )

    return VideoLikeResponse(
        liked=like_result.scalar_one_or_none() is not None,
        likes_count=likes_count,
    )


@router.post(
    "/{video_id}/like",
    response_model=VideoLikeResponse,
)
async def toggle_video_like(
    video_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> VideoLikeResponse:
    video_result = await db.execute(
        select(Video)
        .where(
            Video.id == video_id,
            Video.is_hidden.is_(False),
        )
        .with_for_update(),
    )
    video = video_result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.is_private and video.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    like_result = await db.execute(
        select(VideoLike).where(
            VideoLike.video_id == video_id,
            VideoLike.user_id == current_user.id,
        ),
    )
    like = like_result.scalar_one_or_none()

    if like is None:
        db.add(
            VideoLike(
                video_id=video_id,
                user_id=current_user.id,
            ),
        )
        liked = True
    else:
        await db.delete(like)
        liked = False

    await db.flush()

    likes_count = await get_likes_count(db, video_id)

    await db.commit()

    return VideoLikeResponse(
        liked=liked,
        likes_count=likes_count,
    )


@router.post(
    "/{video_id}/moderate",
    response_model=VideoModerationResponse,
)
async def moderate_video(
    video_id: int,
    request: VideoModerationRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> VideoModerationResponse:
    if current_user.role not in {
        UserRole.MODERATOR,
        UserRole.ADMIN,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to moderate videos",
        )

    result = await db.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(is_hidden=request.is_hidden)
        .returning(Video.id),
    )

    updated_video_id = result.scalar_one_or_none()

    if updated_video_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    await db.commit()

    return VideoModerationResponse(
        video_id=updated_video_id,
        is_hidden=request.is_hidden,
    )