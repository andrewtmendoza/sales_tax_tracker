from __future__ import annotations

import os
import threading
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from receipts.models import Receipt
from receipts.services import llm

if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest_mock import MockerFixture


pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.e2e]

FAKE_JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
PROXY_ONLY_HEADERS = {"host", "content-length", "origin", "referer"}


class ToggleProxy:
    def __init__(self, target_url: str) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ToggleProxyHandler)
        self.server.target_url = target_url.rstrip("/")  # type: ignore[attr-defined]
        self.server.available = True  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def start(self) -> None:
        self.thread.start()

    def set_available(self, available: bool) -> None:
        self.server.available = available  # type: ignore[attr-defined]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class ToggleProxyHandler(BaseHTTPRequestHandler):
    server_version = "ToggleProxy/1.0"

    def do_GET(self) -> None:
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def do_HEAD(self) -> None:
        self.forward()

    def forward(self) -> None:
        if not self.server.available:  # type: ignore[attr-defined]
            self.close_connection = True
            return

        target_url = f"{self.server.target_url}{self.path}"  # type: ignore[attr-defined]
        body = self.read_body()
        request = urllib.request.Request(
            target_url,
            data=body,
            headers=self.forward_headers(),
            method=self.command,
        )

        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        except OSError:
            self.send_error(502, "Upstream unavailable")
            return

        with response:
            response_body = b"" if self.command == "HEAD" else response.read()
            self.send_response(int(response.getcode() or 502))
            for header, value in response.getheaders():
                if header.lower() in HOP_BY_HOP_HEADERS or header.lower() == "content-length":
                    continue
                self.send_header(header, value)
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            if response_body:
                self.wfile.write(response_body)

    def read_body(self) -> bytes | None:
        content_length = int(self.headers.get("Content-Length") or 0)
        if not content_length:
            return None
        return self.rfile.read(content_length)

    def forward_headers(self) -> dict[str, str]:
        return {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS | PROXY_ONLY_HEADERS
        }

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def origin_proxy(live_server) -> Generator[ToggleProxy]:
    proxy = ToggleProxy(live_server.url)
    proxy.start()
    try:
        yield proxy
    finally:
        proxy.close()


@pytest.fixture
def stub_ingest(mocker: MockerFixture) -> None:
    mocker.patch("receipts.services.ingest.storage.upload_image", return_value="receipts/x.jpg")
    mocker.patch(
        "receipts.services.ingest.llm.extract_from_image",
        return_value=llm.Extracted(
            merchant_name="Costco",
            transaction_date=date(2026, 5, 14),
            total_amount=Decimal("117.42"),
            sales_tax_amount=Decimal("9.66"),
            raw_response={"id": "test-response"},
        ),
    )


def authenticate_and_prime_capture(page, context, base_url: str, user) -> None:
    client = Client()
    client.force_login(user)
    context.add_cookies(
        [
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
                "url": base_url,
            }
        ]
    )
    page.goto(f"{base_url}/capture/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Capture receipt")).to_be_visible()
    wait_for_service_worker(page)
    expect(page.get_by_text("Offline ready")).to_be_visible(timeout=15000)


def wait_for_service_worker(page) -> None:
    try:
        page.wait_for_function(
            """
            async () => {
              if (!('serviceWorker' in navigator)) return false;
              await navigator.serviceWorker.ready;
              return Boolean(navigator.serviceWorker.controller);
            }
            """,
            timeout=8000,
        )
    except PlaywrightTimeoutError:
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            """
            async () => {
              if (!('serviceWorker' in navigator)) return false;
              await navigator.serviceWorker.ready;
              return Boolean(navigator.serviceWorker.controller);
            }
            """,
            timeout=8000,
        )


def expect_capture_screen(page) -> None:
    expect(page.get_by_role("heading", name="Capture receipt")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Open camera")).to_be_visible()


def capture_fake_receipt(page) -> None:
    page.set_input_files(
        "#receipt-camera",
        files={"name": "receipt.jpg", "mimeType": "image/jpeg", "buffer": FAKE_JPEG},
    )


def expect_queue_count(page, count: int) -> None:
    expect(page.locator(".capture-count")).to_have_text(str(count), timeout=10000)


def test_capture_shell_works_when_browser_is_offline(page, context, origin_proxy, user) -> None:
    authenticate_and_prime_capture(page, context, origin_proxy.url, user)

    context.set_offline(True)
    origin_proxy.set_available(False)
    try:
        assert page.evaluate("navigator.onLine") is False
        page.goto(f"{origin_proxy.url}/capture/", wait_until="domcontentloaded")
        expect_capture_screen(page)
        page.goto(f"{origin_proxy.url}/", wait_until="domcontentloaded")
        expect_capture_screen(page)

        capture_fake_receipt(page)

        expect_queue_count(page, 1)
        expect(page.get_by_text("Offline. New captures will stay on this device.")).to_be_visible()
        assert Receipt.objects.count() == 0
    finally:
        page.close()
        origin_proxy.set_available(True)
        context.set_offline(False)


def test_capture_sync_recovers_when_origin_becomes_reachable(
    page,
    context,
    origin_proxy,
    user,
    stub_ingest,
) -> None:
    authenticate_and_prime_capture(page, context, origin_proxy.url, user)
    assert page.evaluate("navigator.onLine") is True

    origin_proxy.set_available(False)
    page.goto(f"{origin_proxy.url}/capture/", wait_until="domcontentloaded")
    expect_capture_screen(page)
    page.goto(f"{origin_proxy.url}/", wait_until="domcontentloaded")
    expect_capture_screen(page)
    assert page.evaluate("navigator.onLine") is True

    capture_fake_receipt(page)

    expect_queue_count(page, 1)
    expect(page.get_by_text("Server unreachable. Receipt saved locally.")).to_be_visible(
        timeout=10000
    )
    assert Receipt.objects.count() == 0

    origin_proxy.set_available(True)
    page.get_by_role("button", name="Sync now").click()

    expect_queue_count(page, 0)
    expect(page.get_by_text("All local receipts are synced.")).to_be_visible(timeout=10000)
    assert Receipt.objects.count() == 1
