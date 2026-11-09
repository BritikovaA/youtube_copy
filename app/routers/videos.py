
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.dependencies import CurrentUser, DatabaseSession
from app.models.video import Video
from app.schemas.video import VideoUploadResponse
from app.services.storage import (
    InvalidVideoError,
    UploadTooLargeError,
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
    description: Annotated[
        str | None,
        Form(max_length=10000),
    ] = None,
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

    except UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Video exceeds the maximum allowed size.",
        ) from None

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
            # Не скрываем исходную ошибку PostgreSQL.
            pass

        raise

    return VideoUploadResponse(
        video=video,
    )
