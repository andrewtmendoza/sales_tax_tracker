from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from receipts.models import Receipt
from receipts.services import ingest, llm


@pytest.fixture
def fake_image() -> bytes:
    return b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def stub_storage(mocker):
    return mocker.patch(
        "receipts.services.ingest.storage.upload_image",
        return_value="receipts/abc.jpg",
    )


@pytest.fixture
def stub_llm_ok(mocker):
    extracted = llm.Extracted(
        merchant_name="Target",
        transaction_date=date(2026, 5, 1),
        total_amount=Decimal("42.50"),
        sales_tax_amount=Decimal("3.25"),
        raw_response={"id": "chatcmpl-test"},
    )
    return mocker.patch("receipts.services.ingest.llm.extract_from_image", return_value=extracted)


@pytest.mark.django_db
def test_ingest_creates_receipt(fake_image, stub_storage, stub_llm_ok):
    result = ingest.ingest_image(fake_image, "image/jpeg")

    expected_hash = hashlib.sha256(fake_image).hexdigest()
    assert result.created is True
    assert result.receipt.file_hash == expected_hash
    assert result.receipt.merchant_name == "Target"
    assert result.receipt.transaction_date == date(2026, 5, 1)
    assert result.receipt.total_amount == Decimal("42.50")
    assert result.receipt.sales_tax_amount == Decimal("3.25")
    assert result.receipt.rustfs_path == f"receipts/{expected_hash}.jpg"
    assert result.receipt.processing_error == ""
    stub_storage.assert_called_once()


@pytest.mark.django_db
def test_ingest_dedup_raises_with_existing(fake_image, stub_storage, stub_llm_ok):
    actual_hash = hashlib.sha256(fake_image).hexdigest()
    existing = Receipt.objects.create(file_hash=actual_hash, merchant_name="Prior")

    with pytest.raises(ingest.DuplicateReceipt) as exc:
        ingest.ingest_image(fake_image, "image/jpeg")

    assert exc.value.existing.id == existing.id
    stub_storage.assert_not_called()


@pytest.mark.django_db
def test_ingest_persists_even_when_llm_fails(fake_image, stub_storage, mocker):
    mocker.patch(
        "receipts.services.ingest.llm.extract_from_image",
        side_effect=llm.LLMError("boom"),
    )

    result = ingest.ingest_image(fake_image, "image/jpeg")

    assert result.receipt.processing_error == "boom"
    assert result.receipt.merchant_name == ""
    assert result.receipt.transaction_date is None
    assert result.receipt.rustfs_path.endswith(".jpg")
    stub_storage.assert_called_once()


@pytest.mark.django_db
def test_ingest_removes_reserved_receipt_when_storage_fails(fake_image, mocker):
    mocker.patch(
        "receipts.services.ingest.storage.upload_image",
        side_effect=RuntimeError("storage down"),
    )

    with pytest.raises(RuntimeError):
        ingest.ingest_image(fake_image, "image/jpeg")

    assert Receipt.objects.count() == 0


@pytest.mark.django_db
def test_ingest_extension_by_content_type(fake_image, stub_storage, stub_llm_ok):
    result = ingest.ingest_image(fake_image, "image/png")
    assert result.receipt.rustfs_path.endswith(".png")
