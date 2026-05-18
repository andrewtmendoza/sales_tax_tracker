from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from receipts.models import Receipt
from receipts.services import llm


@pytest.fixture
def client(user):
    client = Client()
    client.force_login(user)
    client.get(reverse("receipts:capture"))
    return client


@pytest.fixture
def fake_image() -> bytes:
    return b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def stub_storage(mocker):
    mocker.patch("receipts.services.ingest.storage.upload_image", return_value="receipts/x.jpg")


@pytest.fixture
def stub_llm(mocker):
    mocker.patch(
        "receipts.services.ingest.llm.extract_from_image",
        return_value=llm.Extracted(
            merchant_name="Costco",
            transaction_date=date(2026, 5, 14),
            total_amount=Decimal("117.42"),
            sales_tax_amount=Decimal("9.66"),
            raw_response={"id": "chatcmpl-x"},
        ),
    )


def _upload(client, fake_image, content_type="image/jpeg", **extra) -> Any:
    upload = SimpleUploadedFile("receipt.jpg", fake_image, content_type=content_type)
    headers = {}
    if "csrftoken" in client.cookies:
        headers["HTTP_X_CSRFTOKEN"] = str(client.cookies["csrftoken"].value)
    return client.post(
        "/api/receipts/upload",
        data={"image": upload, **extra},
        **headers,
    )


@pytest.mark.django_db
def test_upload_requires_login(fake_image):
    client = Client()
    client.get(reverse("login"))
    response = _upload(client, fake_image)
    assert response.status_code == 401


@pytest.mark.django_db
def test_upload_happy_path(client, fake_image, stub_storage, stub_llm):
    response = _upload(client, fake_image)
    assert response.status_code == 201, response.content
    body = response.json()
    expected_hash = hashlib.sha256(fake_image).hexdigest()
    assert body["file_hash"] == expected_hash
    assert body["merchant_name"] == "Costco"
    assert Decimal(body["sales_tax_amount"]) == Decimal("9.66")
    assert Receipt.objects.count() == 1


@pytest.mark.django_db
def test_upload_returns_409_on_duplicate(client, fake_image, stub_storage, stub_llm):
    actual_hash = hashlib.sha256(fake_image).hexdigest()
    Receipt.objects.create(file_hash=actual_hash, merchant_name="Prior")

    response = _upload(client, fake_image)

    assert response.status_code == 409
    body = response.json()
    assert "already" in body["detail"].lower()
    assert body["existing"]["merchant_name"] == "Prior"
    assert Receipt.objects.count() == 1


@pytest.mark.django_db
def test_upload_rejects_non_image(client):
    upload = SimpleUploadedFile("evil.txt", b"not an image at all", content_type="text/plain")
    response = client.post(
        "/api/receipts/upload",
        data={"image": upload},
        HTTP_X_CSRFTOKEN=str(client.cookies["csrftoken"].value),
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Unsupported image type"


@pytest.mark.django_db
@override_settings(RECEIPT_MAX_UPLOAD_BYTES=4)
def test_upload_rejects_large_image(client, fake_image, stub_storage, stub_llm):
    response = _upload(client, fake_image)
    assert response.status_code == 400
    assert response.json()["detail"] == "Upload exceeds maximum receipt image size"
    assert Receipt.objects.count() == 0


@pytest.mark.django_db
def test_upload_persists_when_llm_fails(client, fake_image, stub_storage, mocker):
    mocker.patch(
        "receipts.services.ingest.llm.extract_from_image",
        side_effect=llm.LLMError("model offline"),
    )
    response = _upload(client, fake_image)
    assert response.status_code == 201
    body = response.json()
    assert "processing_error" not in body
    assert body["merchant_name"] == ""
    receipt = Receipt.objects.get()
    assert receipt.processing_error == "model offline"
