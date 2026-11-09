from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.video import Video
from app.schemas.video import (
    VideoDetailResponse,
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