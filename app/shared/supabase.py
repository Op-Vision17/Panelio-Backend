import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.shared.exceptions import BadRequestError

logger = logging.getLogger(__name__)


def extract_path_from_url(url: str) -> Optional[str]:
    """
    Extracts the relative file path from a Supabase public URL.
    """
    marker = f"/public/{settings.SUPABASE_BUCKET}/"
    if marker in url:
        return url.split(marker)[-1]
    return None


async def upload_profile_photo(
    user_id: str, file_content: bytes, filename: str, content_type: str
) -> str:
    """
    Uploads a profile photo to Supabase Storage and returns the public URL.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise BadRequestError(
            "Supabase storage is not configured. Please check environment variables."
        )

    # Get extension, default to jpg
    file_ext = filename.split(".")[-1] if "." in filename else "jpg"
    path = f"{user_id}.{file_ext}"

    # Target REST URL: POST /storage/v1/object/{bucket}/{path}
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}"

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "ApiKey": settings.SUPABASE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, content=file_content)
        except Exception as e:
            logger.exception("HTTP request to Supabase failed")
            raise BadRequestError("Failed to communicate with Supabase storage.")

        if response.status_code != 200:
            logger.error(
                f"Supabase upload failed with status {response.status_code}: {response.text}"
            )
            raise BadRequestError("Failed to upload profile photo to storage.")

    # Format the public URL
    # Format: {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}
    public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{path}"
    return public_url


async def delete_profile_photo_by_path(path: str) -> bool:
    """
    Deletes a file from Supabase Storage by its relative path inside the bucket.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return False

    url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_BUCKET}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "ApiKey": settings.SUPABASE_KEY,
    }

    async with httpx.AsyncClient() as client:
        try:
            # DELETE /storage/v1/object/{bucket} with body {"prefixes": [path]}
            response = await client.request(
                "DELETE", url, headers=headers, json={"prefixes": [path]}
            )
        except Exception as e:
            logger.exception("HTTP request to Supabase delete failed")
            return False

        if response.status_code != 200:
            logger.error(
                f"Supabase delete failed with status {response.status_code}: {response.text}"
            )
            return False

    return True
