from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from receipts.models import Receipt


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_dashboard_renders(client):
    response = client.get(reverse("receipts:dashboard"))
    assert response.status_code == 200
    assert b"Sales Tax Tracker" in response.content
    assert b"calc(env(safe-area-inset-top) + 0.75rem)" in response.content


@pytest.mark.django_db
def test_dashboard_shows_ytd_total(client):
    Receipt.objects.create(
        file_hash="9" * 64,
        transaction_date=date(2026, 1, 15),
        sales_tax_amount=Decimal("12.34"),
    )
    response = client.get(reverse("receipts:dashboard"))
    assert response.status_code == 200
    assert b"12.34" in response.content


@pytest.mark.django_db
def test_dashboard_table_links_load_receipt_detail_with_htmx(client):
    receipt = Receipt.objects.create(
        file_hash="4" * 64,
        rustfs_path="receipts/example.jpg",
        merchant_name="Costco",
        transaction_date=date(2026, 5, 1),
        total_amount=Decimal("100.00"),
        sales_tax_amount=Decimal("8.25"),
    )

    response = client.get(reverse("receipts:dashboard"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "YTD Sales Tax (2026)" in content
    assert "Costco" in content
    assert f'href="{reverse("receipts:dashboard")}?receipt={receipt.id}#receipt-review"' in content
    assert f"hx-get=\"{reverse('receipts:receipt_detail', args=[receipt.id])}\"" in content
    assert 'hx-target="#receipt-review"' in content


@pytest.mark.django_db
def test_dashboard_lists_all_receipts(client):
    for index in range(55):
        Receipt.objects.create(file_hash=f"{index:064x}", merchant_name=f"Merchant {index}")

    response = client.get(reverse("receipts:dashboard"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Merchant 0" in content
    assert "Merchant 54" in content


@pytest.mark.django_db
def test_dashboard_query_param_selects_receipt(client):
    first = Receipt.objects.create(file_hash="1" * 64, merchant_name="First")
    second = Receipt.objects.create(file_hash="2" * 64, merchant_name="Second")

    response = client.get(reverse("receipts:dashboard"), data={"receipt": second.id})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Review receipt #" in content
    assert "Second" in content
    assert str(first.file_hash[:15]) not in content


@pytest.mark.django_db
def test_receipt_detail_renders_side_by_side_editor(client, mocker):
    receipt = Receipt.objects.create(
        file_hash="5" * 64,
        rustfs_path="receipts/detail.jpg",
        merchant_name="Target",
        transaction_date=date(2026, 4, 2),
        total_amount=Decimal("32.10"),
        sales_tax_amount=Decimal("2.65"),
    )
    mocker.patch("receipts.views.storage.presigned_url", return_value="https://signed.example/detail.jpg")

    response = client.get(
        reverse("receipts:receipt_detail", args=[receipt.id]),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Review receipt" in content
    assert "https://signed.example/detail.jpg" in content
    assert f"hx-post=\"{reverse('receipts:receipt_update', args=[receipt.id])}\"" in content
    assert 'name="merchant_name"' in content
    assert 'name="sales_tax_amount"' in content
    assert 'action="/receipts/' in content


@pytest.mark.django_db
def test_receipt_detail_redirects_dashboard_without_htmx(client):
    receipt = Receipt.objects.create(file_hash="8" * 64, merchant_name="Fallback")

    response = client.get(reverse("receipts:receipt_detail", args=[receipt.id]))

    assert response.status_code == 302
    assert response["Location"] == (
        f"{reverse('receipts:dashboard')}?receipt={receipt.id}#receipt-review"
    )


@pytest.mark.django_db
def test_receipt_update_saves_metadata_and_returns_detail(client, mocker):
    receipt = Receipt.objects.create(file_hash="6" * 64, rustfs_path="receipts/update.jpg")
    mocker.patch("receipts.views.storage.presigned_url", return_value="https://signed.example/update.jpg")

    response = client.post(
        reverse("receipts:receipt_update", args=[receipt.id]),
        data={
            "merchant_name": "Trader Joe's",
            "transaction_date": "2026-03-15",
            "total_amount": "44.20",
            "sales_tax_amount": "3.12",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    receipt.refresh_from_db()
    assert receipt.merchant_name == "Trader Joe's"
    assert receipt.transaction_date == date(2026, 3, 15)
    assert receipt.total_amount == Decimal("44.20")
    assert receipt.sales_tax_amount == Decimal("3.12")
    assert "saved" in response.content.decode()


@pytest.mark.django_db
def test_receipt_update_redirects_dashboard_without_htmx(client):
    receipt = Receipt.objects.create(file_hash="3" * 64, merchant_name="Before")

    response = client.post(
        reverse("receipts:receipt_update", args=[receipt.id]),
        data={
            "merchant_name": "After",
            "transaction_date": "2026-03-15",
            "total_amount": "44.20",
            "sales_tax_amount": "3.12",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == (
        f"{reverse('receipts:dashboard')}?receipt={receipt.id}&saved=1#receipt-review"
    )
    receipt.refresh_from_db()
    assert receipt.merchant_name == "After"


@pytest.mark.django_db
def test_receipt_update_requires_post(client):
    receipt = Receipt.objects.create(
        file_hash="7" * 64,
        merchant_name="Keep Me",
        transaction_date=date(2026, 1, 1),
        total_amount=Decimal("10.00"),
        sales_tax_amount=Decimal("1.00"),
    )

    response = client.get(reverse("receipts:receipt_update", args=[receipt.id]))

    assert response.status_code == 405
    receipt.refresh_from_db()
    assert receipt.merchant_name == "Keep Me"
    assert receipt.transaction_date == date(2026, 1, 1)
    assert receipt.total_amount == Decimal("10.00")
    assert receipt.sales_tax_amount == Decimal("1.00")


@pytest.mark.django_db
def test_capture_page_renders(client):
    response = client.get(reverse("receipts:capture"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_capture_page_contains_ios_camera_and_offline_sync_assets(client):
    response = client.get(reverse("receipts:capture"))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'accept="image/*"' in content
    assert 'capture="environment"' not in content
    assert 'aria-label="Open camera"' in content
    assert 'id="receipt-library"' not in content
    assert "Choose from photo roll" not in content
    assert 'class="hidden"' not in content
    assert 'opacity-0' in content
    assert "file-input" not in content
    assert "receiptCapture" in content
    assert "receipts/capture.js" in content
    assert "receipts/capture.css" in content
    assert "vendor/alpinejs/cdn.min.js" in content
    assert "Phone to server upload" in content
    assert "Preparing offline mode..." in content
    assert "Offline first" not in content
    assert "Last hash" not in content
    assert "Open camera" in content
    assert "hx-" not in content
    assert "htmx.org" not in content
    assert "cdn.tailwindcss.com" not in content
    assert "daisyui" not in content


def test_manifest_route(client):
    response = client.get(reverse("receipts:manifest"))
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Sales Tax Tracker"
    assert body["start_url"] == "/capture/"
    assert body["display"] == "standalone"
    assert body["icons"][0]["src"] == "/static/pwa/icon.svg"


def test_service_worker_route(client):
    response = client.get(reverse("receipts:service_worker"))
    assert response.status_code == 200
    assert response["content-type"].startswith("application/javascript")
    assert response["Service-Worker-Allowed"] == "/"
    content = response.content.decode()
    assert "salt-helper-v3" in content
    assert "'/capture/'" in content
    assert "'/static/receipts/capture.css'" in content
    assert "'/static/vendor/alpinejs/cdn.min.js'" in content
    assert "fetch" in content
    assert "caches.match(url.pathname)" in content
    assert "request.mode === 'navigate'" in content
    assert "status: 504" in content
    assert "url.origin === self.location.origin" in content


def test_capture_script_contains_required_offline_primitives(client):
    content = (settings.BASE_DIR / "static" / "receipts" / "capture.js").read_text()
    assert "OFFLINE_CORE_ASSETS" in content
    assert "indexedDB.open('salt-helper-receipts'" in content
    assert "navigator.serviceWorker.ready" in content
    assert "Offline ready" in content
    assert "crypto.subtle.digest('SHA-256'" not in content
    assert "window.addEventListener('online'" in content
    assert "form.append('file_hash'" not in content
    assert "new XMLHttpRequest()" in content
    assert "xhr.upload.onprogress" in content
    assert "Upload complete. Reading receipt details" in content
