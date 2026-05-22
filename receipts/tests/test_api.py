from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from unittest.mock import call

import pytest
from django.test import Client
from django.urls import reverse

from receipts.models import Receipt


def _csrf_headers(client: Client) -> dict[str, str]:
    return {"HTTP_X_CSRFTOKEN": str(client.cookies["csrftoken"].value)}


@pytest.fixture
def client(user):
    client = Client()
    client.force_login(user)
    client.get(reverse("receipts:capture"))
    return client


@pytest.fixture
def anonymous_client():
    return Client()


@pytest.mark.django_db
def test_list_receipts_requires_login(anonymous_client):
    response = anonymous_client.get("/api/receipts/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_list_receipts_empty(client):
    response = client.get("/api/receipts/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_create_receipt_returns_201(client):
    payload = {
        "file_hash": "c" * 64,
        "merchant_name": "Target",
        "transaction_date": "2026-05-01",
        "total_amount": "42.50",
        "sales_tax_amount": "3.25",
    }
    response = client.post(
        "/api/receipts/",
        data=json.dumps(payload),
        content_type="application/json",
        **_csrf_headers(client),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["file_hash"] == "c" * 64
    assert body["merchant_name"] == "Target"
    assert Receipt.objects.count() == 1


@pytest.mark.django_db
def test_create_with_duplicate_hash_returns_409(client):
    Receipt.objects.create(file_hash="d" * 64, merchant_name="Existing")
    payload = {"file_hash": "d" * 64, "merchant_name": "ShouldBeIgnored"}
    response = client.post(
        "/api/receipts/",
        data=json.dumps(payload),
        content_type="application/json",
        **_csrf_headers(client),
    )
    assert response.status_code == 409
    body = response.json()
    assert "already exists" in body["detail"].lower()
    assert body["existing"]["merchant_name"] == "Existing"
    assert Receipt.objects.count() == 1


@pytest.mark.django_db
def test_get_receipt_detail(client):
    receipt = Receipt.objects.create(file_hash="e" * 64, merchant_name="Costco")
    response = client.get(f"/api/receipts/{receipt.id}")
    assert response.status_code == 200
    assert response.json()["merchant_name"] == "Costco"


@pytest.mark.django_db
def test_patch_updates_fields(client):
    receipt = Receipt.objects.create(file_hash="f" * 64, merchant_name="Old")
    response = client.patch(
        f"/api/receipts/{receipt.id}",
        data=json.dumps({"merchant_name": "New", "sales_tax_amount": "5.00"}),
        content_type="application/json",
        **_csrf_headers(client),
    )
    assert response.status_code == 200
    receipt.refresh_from_db()
    assert receipt.merchant_name == "New"
    assert receipt.sales_tax_amount == Decimal("5.00")


@pytest.mark.django_db
def test_delete_receipt(client, mocker):
    receipt = Receipt.objects.create(file_hash="0" * 64, rustfs_path="receipts/original.jpg")
    mocker.patch("receipts.services.receipts.storage.delete_image")
    response = client.delete(f"/api/receipts/{receipt.id}", **_csrf_headers(client))
    assert response.status_code == 204
    assert Receipt.objects.count() == 0


@pytest.mark.django_db
def test_delete_receipt_removes_original_and_thumbnail(client, mocker):
    receipt = Receipt.objects.create(file_hash="0" * 64, rustfs_path="receipts/original.jpg")
    delete_image = mocker.patch("receipts.services.receipts.storage.delete_image")

    response = client.delete(f"/api/receipts/{receipt.id}", **_csrf_headers(client))

    assert response.status_code == 204
    assert Receipt.objects.count() == 0
    delete_image.assert_has_calls(
        [call("receipts/original.jpg"), call("receipts/original.thumb.jpg")]
    )


@pytest.mark.django_db
def test_delete_receipt_keeps_database_row_when_file_delete_fails(client, mocker):
    receipt = Receipt.objects.create(file_hash="1" * 64, rustfs_path="receipts/original.jpg")
    mocker.patch(
        "receipts.services.receipts.storage.delete_image",
        side_effect=RuntimeError("storage down"),
    )

    response = client.delete(f"/api/receipts/{receipt.id}", **_csrf_headers(client))

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to delete receipt files"
    assert Receipt.objects.filter(id=receipt.id).exists()


@pytest.mark.django_db
def test_ytd_stats_endpoint(client):
    Receipt.objects.create(
        file_hash="a" * 64,
        transaction_date=date(2026, 3, 1),
        sales_tax_amount=Decimal("4.00"),
    )
    Receipt.objects.create(
        file_hash="b" * 64,
        transaction_date=date(2026, 4, 1),
        sales_tax_amount=Decimal("6.00"),
    )
    response = client.get("/api/receipts/stats/ytd?year=2026")
    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2026
    assert Decimal(body["total_sales_tax"]) == Decimal("10.00")
    assert body["receipt_count"] == 2
