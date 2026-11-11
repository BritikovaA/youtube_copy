
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, TypedDict

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings


logger = logging.getLogger(__name__)

CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 30
RETRY_DELAY = 2.0

ALLOWED_VIDEO_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}


class MultipartPart(TypedDict):
    PartNumber: int
    ETag: str


class InvalidVideoError(Exception):
    """Unsupported or invalid video file."""


class UploadTooLargeError(Exception):
    """Uploaded video exceeds the configured size limit."""


def get_s3_client(endpoint_url: str | None = None) -> Any:
    session = aioboto3.Session()

    return session.client(
        "s3",
        endpoint_url=endpoint_url or settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name=settings.MINIO_REGION,
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path",
            },
        ),
    )


async def ensure_bucket_exists() -> None:
    async with get_s3_client() as s3:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await s3.head_bucket(
                    Bucket=settings.MINIO_BUCKET,
                )

                logger.info(
                    "RustFS bucket '%s' is available",
                    settings.MINIO_BUCKET,
                )
                return

            except ClientError as exc:
                error_code = exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")

                if error_code in {"404", "NoSuchBucket", "NotFound"}:
                    try:
                        await s3.create_bucket(
                            Bucket=settings.MINIO_BUCKET,
                        )

                        logger.info(
                            "RustFS bucket '%s' created",
                            settings.MINIO_BUCKET,
                        )
                        return

                    except ClientError as create_exc:
                        create_code = create_exc.response.get(
                            "Error",
                            {},
                        ).get("Code", "")

                        if create_code == "BucketAlreadyOwnedByYou":
                            return

                        raise

                if error_code in {"403", "AccessDenied"}:
                    raise RuntimeError(
                        "RustFS access denied. Check access credentials."
                    ) from exc

                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        "Could not connect to RustFS."
                    ) from exc

                logger.warning(
                    "RustFS unavailable. Retry %s/%s.",
                    attempt,
                    MAX_RETRIES,
                )

                await asyncio.sleep(RETRY_DELAY)

            except Exception:
                if attempt == MAX_RETRIES:
                    logger.exception(
                        "Failed to initialize RustFS bucket."
                    )
                    raise

                logger.warning(
                    "RustFS connection failed. Retry %s/%s.",
                    attempt,
                    MAX_RETRIES,
                )

                await asyncio.sleep(RETRY_DELAY)


def validate_video(
    filename: str | None,
    content_type: str | None,
) -> str:
    if not filename:
        raise InvalidVideoError(
            "Filename is required.",
        )

    extension = Path(
        filename.replace("\\", "/"),
    ).suffix.lower()

    expected_content_type = ALLOWED_VIDEO_TYPES.get(extension)

    if expected_content_type is None:
        raise InvalidVideoError(
            "Unsupported video format.",
        )

    if content_type != expected_content_type:
        raise InvalidVideoError(
            "Video MIME type does not match file extension.",
        )

    return extension


async def upload_video(
    file: UploadFile,
    extension: str,
) -> tuple[str, int]:
    object_key = f"{uuid.uuid4()}{extension}"

    max_size = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024

    upload_id: str | None = None
    total_size = 0

    async with get_s3_client() as s3:
        try:
            first_chunk = await file.read(CHUNK_SIZE)

            if not first_chunk:
                raise InvalidVideoError(
                    "Uploaded file is empty.",
                )

            total_size = len(first_chunk)

            if total_size > max_size:
                raise UploadTooLargeError()

            if total_size < CHUNK_SIZE:
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET,
                    Key=object_key,
                    Body=first_chunk,
                    ContentType=file.content_type or "application/octet-stream",
                )

                return object_key, total_size

            multipart_response = await s3.create_multipart_upload(
                Bucket=settings.MINIO_BUCKET,
                Key=object_key,
                ContentType=file.content_type or "application/octet-stream",
            )

            upload_id = multipart_response["UploadId"]

            parts: list[MultipartPart] = []
            part_number = 1
            current_chunk = first_chunk

            while current_chunk:
                uploaded_part = await s3.upload_part(
                    Bucket=settings.MINIO_BUCKET,
                    Key=object_key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=current_chunk,
                )

                parts.append(
                    {
                        "PartNumber": part_number,
                        "ETag": uploaded_part["ETag"],
                    }
                )

                next_chunk = await file.read(CHUNK_SIZE)

                if not next_chunk:
                    break

                total_size += len(next_chunk)

                if total_size > max_size:
                    raise UploadTooLargeError()

                current_chunk = next_chunk
                part_number += 1

            await s3.complete_multipart_upload(
                Bucket=settings.MINIO_BUCKET,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload={
                    "Parts": parts,
                },
            )

            return object_key, total_size

        except Exception:
            if upload_id is not None:
                try:
                    await s3.abort_multipart_upload(
                        Bucket=settings.MINIO_BUCKET,
                        Key=object_key,
                        UploadId=upload_id,
                    )

                except Exception:
                    logger.exception(
                        "Failed to abort multipart upload '%s'.",
                        object_key,
                    )

            raise


async def delete_object(object_key: str) -> None:
    async with get_s3_client() as s3:
        await s3.delete_object(
            Bucket=settings.MINIO_BUCKET,
            Key=object_key,
        )


async def create_video_presigned_url(
    object_key: str,
    expires_in: int = 3600,
) -> str:
    async with get_s3_client(
        endpoint_url=settings.MINIO_PUBLIC_ENDPOINT,
    ) as s3:
        return await s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.MINIO_BUCKET,
                "Key": object_key,
            },
            ExpiresIn=expires_in,
        )
