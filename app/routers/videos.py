
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.dependencies import (
    CurrentUser,
    DatabaseSession,
    OptionalCurrentUser,
    require_roles,
)
from app.models.user import User, UserRole
from app.models.video import Comment, Video, VideoLike
from app.schemas.comment import (
    CommentAuthorResponse,
    CommentCreateRequest,
    CommentResponse,
)
from app.schemas.video import (
    VideoAuthorResponse,
    VideoDetailResponse,
    VideoLikeResponse,
    VideoListItem,
    VideoModerationQueueItem,
    VideoModerationRequest,
    VideoModerationResponse,
    VideoReportResponse,
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


ModeratorUser = Annotated[
    User,
    Depends(require_roles(UserRole.MODERATOR)),
]


async def get_likes_count(
    db: AsyncSession,
    video_id: int,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(VideoLike)
        .where(VideoLike.video_id == video_id),
    )

    return result.scalar_one()


async def get_accessible_video(
    video_id: int,
    db: AsyncSession,
    current_user: User | None,
) -> Video:
    result = await db.execute(
        select(Video).where(Video.id == video_id),
    )
    video = result.scalar_one_or_none()

    if video is None or video.is_hidden:
        if video is not None and current_user is not None:
            if video.owner_id == current_user.id:
                return video

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

    return video


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
    file_path: str | None = None

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

        if file_path is not None:
            await delete_object(file_path)

        raise


@router.get(
    "/moderation",
    response_model=list[VideoModerationQueueItem],
)
async def get_moderation_queue(
    moderator: ModeratorUser,
    db: DatabaseSession,
) -> list[VideoModerationQueueItem]:
    result = await db.execute(
        select(Video)
        .options(joinedload(Video.owner))
        .where(Video.is_reported.is_(True))
        .order_by(Video.created_at.asc()),
    )

    videos = result.scalars().unique().all()

    moderation_items: list[VideoModerationQueueItem] = []

    for video in videos:
        video_data = VideoListItem.model_validate(video)
        video_url = await create_video_presigned_url(video.file_path)

        moderation_items.append(
            VideoModerationQueueItem(
                **video_data.model_dump(),
                video_url=video_url,
            ),
        )

    return moderation_items


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

    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.is_hidden and (
        current_user is None
        or current_user.id != video.owner_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )

    if video.is_private and (
        current_user is None
        or current_user.id != video.owner_id
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
        is_reported=video.is_reported,
        created_at=video.created_at,
        owner=video.owner,
        video_url=video_url,
        likes_count=likes_count,
    )


@router.get(
    "/{video_id}/comments",
    response_model=list[CommentResponse],
)
async def get_video_comments(
    video_id: int,
    db: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> list[CommentResponse]:
    await get_accessible_video(video_id, db, current_user)

    result = await db.execute(
        select(Comment, User)
        .join(User, User.id == Comment.user_id)
        .where(Comment.video_id == video_id)
        .order_by(Comment.created_at.desc()),
    )

    return [
        CommentResponse(
            id=comment.id,
            video_id=comment.video_id,
            user_id=comment.user_id,
            text=comment.text,
            created_at=comment.created_at,
            author=CommentAuthorResponse.model_validate(user),
        )
        for comment, user in result.all()
    ]


@router.post(
    "/{video_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_video_comment(
    video_id: int,
    request: CommentCreateRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> CommentResponse:
    video = await get_accessible_video(
        video_id,
        db,
        current_user,
    )

    comment = Comment(
        video_id=video.id,
        user_id=current_user.id,
        text=request.text,
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        video_id=comment.video_id,
        user_id=comment.user_id,
        text=comment.text,
        created_at=comment.created_at,
        author=CommentAuthorResponse.model_validate(current_user),
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
    await get_accessible_video(video_id, db, current_user)

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
    "/{video_id}/report",
    response_model=VideoReportResponse,
)
async def report_video(
    video_id: int,
    db: DatabaseSession,
    current_user: OptionalCurrentUser,
) -> VideoReportResponse:
    video = await get_accessible_video(
        video_id,
        db,
        current_user,
    )

    if video.is_hidden:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video is already hidden",
        )

    if video.is_reported:
        return VideoReportResponse(
            video_id=video.id,
            is_reported=True,
            message="Video has already been reported",
        )

    video.is_reported = True

    await db.commit()

    return VideoReportResponse(
        video_id=video.id,
        is_reported=True,
        message="Report submitted successfully",
    )


@router.patch(
    "/{video_id}/moderation",
    response_model=VideoModerationResponse,
)
async def moderate_video(
    video_id: int,
    request: VideoModerationRequest,
    moderator: ModeratorUser,
    db: DatabaseSession,
) -> VideoModerationResponse:
    result = await db.execute(
        update(Video)
        .where(Video.id == video_id)
        .values(
            is_hidden=request.is_hidden,
            is_reported=False,
        )
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
        is_reported=False,
    )
