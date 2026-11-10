from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import joinedload

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.video import Video, VideoLike
from app.schemas.video import (
    VideoDetailResponse,
    VideoLikeResponse,
    VideoListItem,
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


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video_endpoint(
    current_user: CurrentUser,
    db: DatabaseSession,
    title: Annotated[str, Form(min_length=1, max_length=255)],
    description: Annotated[str | None, Form(max_length=10000)] = None,
    file: UploadFile = File(...),
) -> VideoUploadResponse:
    try:
        extension = validate_video(
            file.filename,
            file.content_type,
        )

        object_key, _ = await upload_video(
            file,
            extension,
        )

    except InvalidVideoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    try:
        video = Video(
            title=title.strip(),
            description=description,
            file_path=object_key,
            owner_id=current_user.id,
        )

        db.add(video)
        await db.commit()
        await db.refresh(video)

    except Exception:
        await db.rollback()

        try:
            await delete_object(object_key)
        except Exception:
            pass

        raise

    return VideoUploadResponse(
        video=VideoResponse.model_validate(video),
    )


@router.get(
    "",
    response_model=list[VideoListItem],
    status_code=status.HTTP_200_OK,
)
async def get_videos(
    db: DatabaseSession,
) -> list[VideoListItem]:
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .order_by(Video.created_at.desc())
    )

    videos = result.scalars().all()

    return [
        VideoListItem.model_validate(video)
        for video in videos
    ]


@router.get(
    "/{video_id}",
    response_model=VideoDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_video(
    video_id: int,
    db: DatabaseSession,
) -> VideoDetailResponse:
    update_result = await db.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(
            views_count=Video.views_count + 1,
        )
        .returning(Video.id)
        .execution_options(synchronize_session=False)
    )

    updated_video_id = update_result.scalar_one_or_none()

    if updated_video_id is None:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    await db.commit()

    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.id == video_id)
    )

    video = result.scalar_one_or_none()

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    video_url = await create_video_presigned_url(
        object_key=video.file_path,
        expires_in=3600,
    )

    return VideoDetailResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        views_count=video.views_count,
        created_at=video.created_at,
        owner=video.owner,
        video_url=video_url,
    )


@router.post(
    "/{video_id}/like",
    response_model=VideoLikeResponse,
    status_code=status.HTTP_200_OK,
)
async def toggle_video_like(
    video_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> VideoLikeResponse:
    video = await db.scalar(
        select(Video)
        .where(Video.id == video_id)
        .with_for_update()
    )

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    existing_like = await db.scalar(
        select(VideoLike).where(
            VideoLike.user_id == current_user.id,
            VideoLike.video_id == video_id,
        )
    )

    if existing_like is not None:
        await db.delete(existing_like)
        liked = False
    else:
        db.add(
            VideoLike(
                user_id=current_user.id,
                video_id=video_id,
            )
        )
        liked = True

    await db.commit()

    likes_count = await db.scalar(
        select(func.count())
        .select_from(VideoLike)
        .where(VideoLike.video_id == video_id)
    )

    return VideoLikeResponse(
        liked=liked,
        likes_count=int(likes_count or 0),
    )