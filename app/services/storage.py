"""
File storage service for Episodic.

Currently implements local disk storage. To switch to S3/Cloudflare R2:
1. Set STORAGE_BACKEND=s3 in .env
2. Add AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION to .env
3. pip install boto3
4. Implement the S3 branch in save_file / delete_file below.

The upload endpoint and callers don't change — only this file.
"""
import logging
import mimetypes
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

# Allowed MIME types and their canonical extensions.
# Restricted to image formats and PDF — appropriate for a literary/art magazine.
ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

MAX_FILE_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


async def save_file(file: UploadFile, submission_id: uuid.UUID) -> dict:
    """
    Validate and save an uploaded file. Returns file metadata dict
    suitable for storing in Submission.file_metadata.

    Raises HTTPException on validation failure.
    """
    # --- Validate MIME type ---
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '{content_type}' is not allowed. "
                f"Accepted types: {', '.join(ALLOWED_MIME_TYPES.keys())}"
            ),
        )

    # --- Read and validate file size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_FILE_SIZE_MB}MB size limit.",
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if settings.STORAGE_BACKEND == "local":
        return await _save_local(contents, file.filename or "upload", content_type, submission_id)

    # S3 backend — implement when ready
    # return await _save_s3(contents, file.filename, content_type, submission_id)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Storage backend '{settings.STORAGE_BACKEND}' is not configured.",
    )


async def delete_file(file_metadata: dict) -> None:
    """
    Delete a previously stored file using its stored metadata.
    Fails silently if the file is already gone (idempotent).
    """
    if settings.STORAGE_BACKEND == "local":
        await _delete_local(file_metadata.get("storage_key", ""))
        return

    # S3 backend — implement when ready
    logger.warning(
        f"delete_file called with unsupported backend '{settings.STORAGE_BACKEND}'"
    )


# ---------------------------------------------------------------------------
# Local disk implementation
# ---------------------------------------------------------------------------

async def _save_local(
    contents: bytes,
    original_filename: str,
    content_type: str,
    submission_id: uuid.UUID,
) -> dict:
    ext = ALLOWED_MIME_TYPES[content_type]
    safe_name = f"{uuid.uuid4()}{ext}"
    # storage_key is the path relative to UPLOAD_DIR — used for retrieval and deletion
    storage_key = f"submissions/{submission_id}/{safe_name}"
    dest = Path(settings.UPLOAD_DIR) / storage_key

    dest.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest, "wb") as f:
        await f.write(contents)

    logger.info(f"File saved locally: {storage_key} ({len(contents)} bytes)")

    return {
        "original_filename": original_filename,
        "storage_key": storage_key,
        "mime_type": content_type,
        "size_bytes": len(contents),
    }


async def _delete_local(storage_key: str) -> None:
    if not storage_key:
        return
    path = Path(settings.UPLOAD_DIR) / storage_key
    try:
        path.unlink(missing_ok=True)
        logger.info(f"File deleted locally: {storage_key}")
    except OSError as e:
        logger.warning(f"Could not delete file {storage_key}: {e}")


# ---------------------------------------------------------------------------
# S3 implementation stub (uncomment and fill in when ready)
# ---------------------------------------------------------------------------

# import boto3
# from botocore.exceptions import BotoCoreError, ClientError
#
# async def _save_s3(
#     contents: bytes,
#     original_filename: str,
#     content_type: str,
#     submission_id: uuid.UUID,
# ) -> dict:
#     ext = ALLOWED_MIME_TYPES[content_type]
#     storage_key = f"submissions/{submission_id}/{uuid.uuid4()}{ext}"
#     s3 = boto3.client(
#         "s3",
#         aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#         region_name=settings.S3_REGION,
#     )
#     try:
#         s3.put_object(
#             Bucket=settings.S3_BUCKET_NAME,
#             Key=storage_key,
#             Body=contents,
#             ContentType=content_type,
#         )
#     except (BotoCoreError, ClientError) as e:
#         logger.error(f"S3 upload failed: {e}")
#         raise HTTPException(status_code=500, detail="File upload failed.")
#
#     return {
#         "original_filename": original_filename,
#         "storage_key": storage_key,
#         "mime_type": content_type,
#         "size_bytes": len(contents),
#     }
