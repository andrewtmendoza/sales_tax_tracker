from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from receipts.services import storage


def _client_error(code: str, status: int = 404) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "missing"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "HeadBucket",
    )


def test_ensure_bucket_no_op_when_exists():
    client = MagicMock()
    client.head_bucket.return_value = {}
    bucket = storage.ensure_bucket(client=client, bucket="receipts")
    assert bucket == "receipts"
    client.create_bucket.assert_not_called()


def test_ensure_bucket_creates_when_missing():
    client = MagicMock()
    client.head_bucket.side_effect = _client_error("404", 404)
    storage.ensure_bucket(client=client, bucket="receipts")
    client.create_bucket.assert_called_once_with(Bucket="receipts")


def test_ensure_bucket_reraises_other_errors():
    client = MagicMock()
    client.head_bucket.side_effect = _client_error("AccessDenied", 403)
    with pytest.raises(ClientError):
        storage.ensure_bucket(client=client, bucket="receipts")


def test_upload_image_calls_put_object():
    client = MagicMock()
    client.head_bucket.return_value = {}
    key = storage.upload_image(
        b"abc",
        "receipts/x.jpg",
        "image/jpeg",
        client=client,
        bucket="receipts",
    )
    assert key == "receipts/x.jpg"
    client.put_object.assert_called_once_with(
        Bucket="receipts",
        Key="receipts/x.jpg",
        Body=b"abc",
        ContentType="image/jpeg",
    )


def test_presigned_url_delegates_to_client():
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://signed.example/x"
    url = storage.presigned_url("receipts/x.jpg", expires_in=600, client=client, bucket="receipts")
    assert url == "https://signed.example/x"
    client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "receipts", "Key": "receipts/x.jpg"},
        ExpiresIn=600,
    )


def test_presigned_url_uses_public_endpoint(settings):
    settings.RUSTFS_PUBLIC_ENDPOINT_URL = "http://browser-visible-rustfs:9000"
    url = storage.presigned_url("receipts/x.jpg")
    assert url.startswith("http://browser-visible-rustfs:9000/receipts/receipts/x.jpg")
