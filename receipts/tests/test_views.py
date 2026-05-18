from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from django.conf import settings
from django.test import Client
from django.urls import reverse
from PIL import Image

from receipts.models import Receipt


@pytest.fixture
def client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def anonymous_client():
    return Client()


@pytest.mark.django_db
def test_dashboard_redirects_to_login_when_logged_out(anonymous_client):
    response = anonymous_client.get(reverse("receipts:dashboard"))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_dashboard_renders(client):
    response = client.get(reverse("receipts:dashboard"))
    assert response.status_code == 200
    assert b"Sales Tax Tracker" in response.content
    assert b"calc(env(safe-area-inset-top) + 0.75rem)" in response.content
    assert b"receipts/dashboard.css" in response.content
    assert b"cdn.tailwindcss.com" in response.content
    assert b"theme.css" in response.content


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
    assert "Second" in content
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

    response = client.get(
        reverse("receipts:receipt_detail", args=[receipt.id]),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Target" in content
    assert "April 2, 2026" in content
    assert "Total $32.10" in content
    assert "Tax $2.65" in content
    assert reverse("receipts:receipt_thumbnail", args=[receipt.id]) in content
    assert reverse("receipts:receipt_image", args=[receipt.id]) in content
    assert f"hx-post=\"{reverse('receipts:receipt_update', args=[receipt.id])}\"" in content
    assert 'name="merchant_name"' in content
    assert 'name="sales_tax_amount"' in content
    assert 'action="/receipts/' in content
    assert receipt.file_hash[:15] not in content


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
def test_receipt_image_returns_stored_bytes(client, mocker):
    receipt = Receipt.objects.create(file_hash="a" * 64, rustfs_path="receipts/view.jpg")
    mocker.patch(
        "receipts.views.storage.download_image",
        return_value=(b"image-bytes", "image/jpeg"),
    )

    response = client.get(reverse("receipts:receipt_image", args=[receipt.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert response.content == b"image-bytes"


@pytest.mark.django_db
def test_receipt_thumbnail_returns_cached_bytes(client, mocker):
    receipt = Receipt.objects.create(file_hash="d" * 64, rustfs_path="receipts/thumb-source.jpg")
    mocker.patch(
        "receipts.views.storage.download_image",
        return_value=(b"thumbnail-bytes", "image/jpeg"),
    )

    response = client.get(reverse("receipts:receipt_thumbnail", args=[receipt.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert response.content == b"thumbnail-bytes"


@pytest.mark.django_db
def test_receipt_thumbnail_generates_and_uploads_smaller_image(client, mocker):
    receipt = Receipt.objects.create(file_hash="e" * 64, rustfs_path="receipts/source.png")
    original = BytesIO()
    Image.new("RGB", (2400, 1800), "white").save(original, format="PNG")
    original_bytes = original.getvalue()

    def download_image(key: str, **kwargs):
        if key == "receipts/source.thumb.jpg":
            raise ClientError(
                {
                    "Error": {"Code": "NoSuchKey", "Message": "missing"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "GetObject",
            )
        if key == "receipts/source.png":
            return original_bytes, "image/png"
        raise AssertionError(f"Unexpected key: {key}")

    mocker.patch("receipts.views.storage.download_image", side_effect=download_image)
    upload_image = mocker.patch("receipts.views.storage.upload_image")

    response = client.get(reverse("receipts:receipt_thumbnail", args=[receipt.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    upload_image.assert_called_once_with(
        response.content,
        "receipts/source.thumb.jpg",
        "image/jpeg",
    )
    with Image.open(BytesIO(response.content)) as thumbnail:
        assert max(thumbnail.size) <= 1000


@pytest.mark.django_db
def test_receipt_thumbnail_falls_back_to_original_when_resize_fails(client, mocker):
    receipt = Receipt.objects.create(file_hash="f" * 64, rustfs_path="receipts/source.heic")

    def download_image(key: str, **kwargs):
        if key == "receipts/source.thumb.jpg":
            raise ClientError(
                {
                    "Error": {"Code": "NoSuchKey", "Message": "missing"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "GetObject",
            )
        if key == "receipts/source.heic":
            return b"raw-original", "image/heic"
        raise AssertionError(f"Unexpected key: {key}")

    mocker.patch("receipts.views.storage.download_image", side_effect=download_image)
    mocker.patch("receipts.views._build_thumbnail", side_effect=OSError("unsupported"))
    upload_image = mocker.patch("receipts.views.storage.upload_image")

    response = client.get(reverse("receipts:receipt_thumbnail", args=[receipt.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/heic"
    assert response.content == b"raw-original"
    upload_image.assert_not_called()


@pytest.mark.django_db
def test_receipt_image_404s_without_path(client):
    receipt = Receipt.objects.create(file_hash="b" * 64)

    response = client.get(reverse("receipts:receipt_image", args=[receipt.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_dashboard_uses_local_receipt_image_url(client):
    receipt = Receipt.objects.create(file_hash="c" * 64, rustfs_path="receipts/local.jpg")

    response = client.get(reverse("receipts:dashboard"), data={"receipt": receipt.id})

    assert response.status_code == 200
    content = response.content.decode()
    assert reverse("receipts:receipt_thumbnail", args=[receipt.id]) in content
    assert reverse("receipts:receipt_image", args=[receipt.id]) in content


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
    assert "salt-helper-v5" in content
    assert "'/capture/'" in content
    assert "'/static/receipts/capture.css'" in content
    assert "'/static/vendor/alpinejs/cdn.min.js'" in content
    assert "fetch" in content
    assert "caches.match(url.pathname)" in content
    assert "request.mode === 'navigate' && url.pathname === '/capture/'" in content
    assert "status: 504" in content
    assert "url.origin === self.location.origin" in content
    assert "if (url.pathname === '/') return caches.match('/')" not in content


def test_health_route_is_public(anonymous_client):
    response = anonymous_client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_capture_styles_use_emerald_theme_accents():
    content = (settings.BASE_DIR / "static" / "receipts" / "capture.css").read_text()
    assert "linear-gradient(135deg, #0c885f, #0f766e)" in content
    assert "linear-gradient(90deg, #0c885f, #0f766e)" in content
    assert "#7c3aed" not in content
