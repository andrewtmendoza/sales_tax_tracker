from __future__ import annotations

import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def get_client():
    return _client(settings.RUSTFS_ENDPOINT_URL)


def get_public_client():
    return _client(settings.RUSTFS_PUBLIC_ENDPOINT_URL)


def _client(endpoint_url: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.RUSTFS_ACCESS_KEY,
        aws_secret_access_key=settings.RUSTFS_SECRET_KEY,
        region_name=settings.RUSTFS_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(client=None, bucket: str | None = None) -> str:
    client = client or get_client()
    bucket = bucket or str(settings.RUSTFS_BUCKET)
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in {"404", "NoSuchBucket"} or status == 404:
            client.create_bucket(Bucket=bucket)
            logger.info("Created bucket %s on RustFS", bucket)
        else:
            raise
    return bucket


def upload_image(
    file_bytes: bytes,
    key: str,
    content_type: str = "image/jpeg",
    *,
    client=None,
    bucket: str | None = None,
) -> str:
    client = client or get_client()
    bucket = ensure_bucket(client, bucket)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key


def presigned_url(
    key: str,
    expires_in: int = 3600,
    *,
    client=None,
    bucket: str | None = None,
) -> str:
    client = client or get_public_client()
    bucket = bucket or str(settings.RUSTFS_BUCKET)
    return str(client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    ))


def download_image(
    key: str,
    *,
    client=None,
    bucket: str | None = None,
) -> tuple[bytes, str]:
    client = client or get_client()
    bucket = bucket or str(settings.RUSTFS_BUCKET)
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read(), str(response.get("ContentType") or "application/octet-stream")


def delete_image(
    key: str,
    *,
    client=None,
    bucket: str | None = None,
) -> None:
    client = client or get_client()
    bucket = bucket or str(settings.RUSTFS_BUCKET)
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code not in {"404", "NoSuchKey", "NoSuchBucket"} and status != 404:
            raise
