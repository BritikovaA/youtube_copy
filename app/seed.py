
import asyncio
import logging
import random
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database import AsyncSessionLocal, engine
from app.models.user import User, UserRole
from app.models.video import Video
from app.services.storage import (
    ALLOWED_VIDEO_TYPES,
    ensure_bucket_exists,
    get_s3_client,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
SEED_DATA_DIR = BASE_DIR / "seed_data"

password_hash = PasswordHash.recommended()

USERS: tuple[dict[str, str | UserRole], ...] = (
    {
        "email": "admin@email.com",
        "password": "admin123",
        "role": UserRole.ADMIN,
    },
    {
        "email": "moderator@email.com",
        "password": "moderator123",
        "role": UserRole.MODERATOR,
    },
    {
        "email": "user1@email.com",
        "password": "user1111",
        "role": UserRole.USER,
    },
    {
        "email": "user2@email.com",
        "password": "user2222",
        "role": UserRole.USER,
    },
)

VIDEO_TITLES: tuple[str, ...] = (
    "Обзор технологий и современных гаджетов",
    "Урок Python: разработка API на FastAPI",
    "Путешествие по красивым местам",
    "Рецепт домашней пиццы",
    "Сборка игрового компьютера",
    "Настройка рабочего места разработчика",
    "Обзор компьютерных игр",
    "Советы по видеомонтажу",
    "Основы работы с PostgreSQL",
    "Создание backend на FastAPI",
    "Docker Compose: настройка проекта",
    "Тестирование REST API",
)

VIDEO_DESCRIPTION = (
    "Тестовое видео для проверки поиска, фильтрации "
    "и отображения видеоконтента."
)

VIDEOS_PER_USER = 2


def get_seed_files() -> list[Path]:
    if not SEED_DATA_DIR.exists():
        raise FileNotFoundError(
            f"Seed directory does not exist: {SEED_DATA_DIR}"
        )

    files = sorted(
        path
        for path in SEED_DATA_DIR.iterdir()
        if path.is_file()
    )

    if len(files) < VIDEOS_PER_USER:
        raise RuntimeError(
            f"At least {VIDEOS_PER_USER} files are required "
            f"in {SEED_DATA_DIR}. Found: {len(files)}"
        )

    for file_path in files:
        extension = file_path.suffix.lower()

        if extension not in ALLOWED_VIDEO_TYPES:
            raise ValueError(
                f"Unsupported video format: {file_path.name}"
            )

    return files


async def get_or_create_user(
    session: AsyncSession,
    user_data: dict[str, str | UserRole],
) -> User:
    email = str(user_data["email"])
    password = str(user_data["password"])
    role = user_data["role"]

    if not isinstance(role, UserRole):
        raise TypeError(f"Invalid role for user {email}")

    result = await session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            hashed_password=password_hash.hash(password),
            role=role,
        )
        session.add(user)
        await session.flush()

        logger.info("Created user: %s", email)
        return user

    if user.role != role:
        user.role = role

    logger.info("User already exists: %s", email)
    return user


async def object_exists(
    s3: Any,
    object_key: str,
) -> bool:
    try:
        await s3.head_object(
            Bucket=settings.MINIO_BUCKET,
            Key=object_key,
        )
        return True

    except ClientError as exc:
        error = exc.response.get("Error", {})
        error_code = str(error.get("Code", ""))

        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False

        status_code = exc.response.get(
            "ResponseMetadata",
            {},
        ).get("HTTPStatusCode")

        if status_code == 404:
            return False

        raise


async def upload_seed_video(
    s3: Any,
    file_path: Path,
    object_key: str,
) -> None:
    if await object_exists(s3, object_key):
        logger.info(
            "Storage object already exists: %s",
            object_key,
        )
        return

    extension = file_path.suffix.lower()
    content_type = ALLOWED_VIDEO_TYPES[extension]

    file_content = await asyncio.to_thread(
        file_path.read_bytes,
    )

    if not file_content:
        raise ValueError(
            f"Seed video is empty: {file_path}"
        )

    max_size = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024

    if len(file_content) > max_size:
        raise ValueError(
            f"Seed video exceeds MAX_VIDEO_SIZE_MB: {file_path}"
        )

    await s3.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=object_key,
        Body=file_content,
        ContentType=content_type,
    )

    logger.info("Uploaded seed video: %s", object_key)


async def create_video(
    session: AsyncSession,
    s3: Any,
    user: User,
    file_path: Path,
    title: str,
    is_private: bool,
) -> None:
    object_key = (
        f"seed/{user.id}/{file_path.name}"
    )

    await upload_seed_video(
        s3=s3,
        file_path=file_path,
        object_key=object_key,
    )

    result = await session.execute(
        select(Video).where(Video.file_path == object_key)
    )
    existing_video = result.scalar_one_or_none()

    if existing_video is not None:
        logger.info(
            "Video already exists: %s",
            object_key,
        )
        return

    video = Video(
        title=title,
        description=VIDEO_DESCRIPTION,
        file_path=object_key,
        owner_id=user.id,
        is_private=is_private,
    )

    session.add(video)

    logger.info(
        "Created video '%s' for %s (private=%s)",
        title,
        user.email,
        is_private,
    )


async def seed_database() -> None:
    seed_files = get_seed_files()

    title_pool = list(VIDEO_TITLES)
    random.Random("youtube-copy-seed-v1").shuffle(title_pool)

    await ensure_bucket_exists()

    async with get_s3_client() as s3:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                title_index = 0
                video_index = 0

                for user_index, user_data in enumerate(USERS):
                    user = await get_or_create_user(
                        session=session,
                        user_data=user_data,
                    )

                    selected_files = [
                        seed_files[
                            user_index % len(seed_files)
                        ],
                        seed_files[
                            (user_index + 1) % len(seed_files)
                        ],
                    ]

                    for file_path in selected_files:
                        title = title_pool[title_index]
                        title_index += 1

                        is_private = video_index % 3 == 0
                        video_index += 1

                        await create_video(
                            session=session,
                            s3=s3,
                            user=user,
                            file_path=file_path,
                            title=title,
                            is_private=is_private,
                        )

    logger.info("Seed completed successfully.")


async def main() -> None:
    try:
        await seed_database()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(main())
