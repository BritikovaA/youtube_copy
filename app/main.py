import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aioboto3
from botocore.exceptions import ClientError
from fastapi import FastAPI


logger = logging.getLogger(__name__)

MINIO_ENDPOINT: str = os.getenv(
    "MINIO_ENDPOINT",
    "http://rustfs:9000",
)

MINIO_ACCESS_KEY: str = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY: str = os.environ["MINIO_SECRET_KEY"]
MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "videos")

MINIO_REGION: str = os.getenv("MINIO_REGION", "us-east-1")

MINIO_MAX_RETRIES: int = 30
MINIO_RETRY_DELAY: float = 2.0


async def create_bucket_if_not_exists() -> None:
    session = aioboto3.Session()

    async with session.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name=MINIO_REGION,
    ) as s3_client:

        for attempt in range(1, MINIO_MAX_RETRIES + 1):
            try:
                await s3_client.head_bucket(
                    Bucket=MINIO_BUCKET,
                )

                logger.info(
                    "MinIO bucket '%s' already exists",
                    MINIO_BUCKET,
                )
                return

            except ClientError as exc:
                error_code = exc.response.get(
                    "Error",
                    {},
                ).get("Code", "")

                if error_code not in {
                    "404",
                    "NoSuchBucket",
                    "NotFound",
                }:
                    raise

                try:
                    await s3_client.create_bucket(
                        Bucket=MINIO_BUCKET,
                    )

                    logger.info(
                        "MinIO bucket '%s' created",
                        MINIO_BUCKET,
                    )
                    return

                except ClientError as create_exc:
                    create_error_code = create_exc.response.get(
                        "Error",
                        {},
                    ).get("Code", "")

                    if create_error_code in {
                        "BucketAlreadyOwnedByYou",
                    }:
                        logger.info(
                            "MinIO bucket '%s' already exists",
                            MINIO_BUCKET,
                        )
                        return

                    raise

            except Exception:
                if attempt == MINIO_MAX_RETRIES:
                    logger.exception(
                        "Failed to connect to MinIO after %s attempts",
                        MINIO_MAX_RETRIES,
                    )
                    raise

                logger.warning(
                    "MinIO is unavailable. Retry %s/%s in %.1f seconds",
                    attempt,
                    MINIO_MAX_RETRIES,
                    MINIO_RETRY_DELAY,
                )

                await asyncio.sleep(MINIO_RETRY_DELAY)

        raise RuntimeError(
            f"Could not initialize MinIO bucket '{MINIO_BUCKET}'"
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await create_bucket_if_not_exists()

    yield


app = FastAPI(
    title="YouTube Copy",
    description="YouTube clone backend",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "YouTube Copy API is running",
    }