from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import urlencode

from botocore.exceptions import ClientError
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps, UnidentifiedImageError

from receipts.models import Receipt
from receipts.services import receipts as receipt_service
from receipts.services import storage

THUMBNAIL_MAX_SIZE = (1000, 1000)


@login_required
@ensure_csrf_cookie
def dashboard(request):
    year = timezone.now().year
    selected_receipt = _selected_receipt(request.GET.get("receipt"))
    context = {
        "receipts": Receipt.objects.all(),
        "ytd_total": Receipt.ytd_sales_tax(year),
        "year": year,
        "selected_receipt": selected_receipt,
        "selected_image_url": _thumbnail_url(selected_receipt) if selected_receipt else "",
        "selected_full_image_url": _image_url(selected_receipt) if selected_receipt else "",
        "selected_saved": request.GET.get("saved") == "1",
        "selected_delete_error": request.GET.get("delete_error") == "1",
    }
    return render(request, "receipts/dashboard.html", context)


@login_required
def receipt_detail(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not getattr(request, "htmx", False):
        return redirect(_dashboard_receipt_url(receipt.id))
    return render(request, "receipts/_receipt_detail.html", _detail_context(receipt))


@login_required
def receipt_image(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not receipt.rustfs_path:
        raise Http404("Receipt image is unavailable")
    try:
        file_bytes, content_type = storage.download_image(str(receipt.rustfs_path))
    except Exception as exc:
        raise Http404("Receipt image is unavailable") from exc
    return HttpResponse(file_bytes, content_type=content_type)


@login_required
def receipt_thumbnail(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not receipt.rustfs_path:
        raise Http404("Receipt image is unavailable")

    original_key = str(receipt.rustfs_path)
    thumbnail_key = _thumbnail_key(original_key)
    try:
        file_bytes, content_type = storage.download_image(thumbnail_key)
        return HttpResponse(file_bytes, content_type=content_type)
    except ClientError as exc:
        if not _is_missing_storage_object(exc):
            raise Http404("Receipt image is unavailable") from exc

    try:
        original_bytes, original_content_type = storage.download_image(original_key)
    except Exception as exc:
        raise Http404("Receipt image is unavailable") from exc

    try:
        thumbnail_bytes = _build_thumbnail(original_bytes)
    except (OSError, UnidentifiedImageError):
        return HttpResponse(original_bytes, content_type=original_content_type)

    storage.upload_image(thumbnail_bytes, thumbnail_key, "image/jpeg")
    return HttpResponse(thumbnail_bytes, content_type="image/jpeg")


@login_required
@require_POST
def receipt_update(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    receipt.merchant_name = request.POST.get("merchant_name", "").strip()
    receipt.transaction_date = _date_or_none(request.POST.get("transaction_date"))
    receipt.total_amount = _decimal_or_none(request.POST.get("total_amount"))
    receipt.sales_tax_amount = _decimal_or_none(request.POST.get("sales_tax_amount"))
    receipt.save()
    if not getattr(request, "htmx", False):
        return redirect(_dashboard_receipt_url(receipt.id, saved=True))
    return render(request, "receipts/_receipt_detail.html", _detail_context(receipt, saved=True))


@login_required
@require_POST
def receipt_delete(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    try:
        receipt_service.delete_receipt(receipt)
    except Exception:
        if not getattr(request, "htmx", False):
            return redirect(_dashboard_receipt_url(receipt.id, delete_error=True))
        response = render(
            request,
            "receipts/_receipt_detail.html",
            _detail_context(receipt, delete_error=True),
        )
        response.status_code = 502
        return response

    dashboard_url = reverse("receipts:dashboard")
    if not getattr(request, "htmx", False):
        return redirect(dashboard_url)
    response = HttpResponse(status=204)
    response["HX-Redirect"] = dashboard_url
    return response


@login_required
@ensure_csrf_cookie
def capture(request):
    return render(request, "receipts/capture.html", {})


def _detail_context(
    receipt: Receipt,
    saved: bool = False,
    delete_error: bool = False,
):
    return {
        "receipt": receipt,
        "image_url": _thumbnail_url(receipt),
        "full_image_url": _image_url(receipt),
        "saved": saved,
        "delete_error": delete_error,
    }


def _selected_receipt(receipt_id: str | None):
    if receipt_id:
        try:
            return Receipt.objects.filter(id=int(receipt_id)).first() or Receipt.objects.first()
        except (TypeError, ValueError):
            pass
    return Receipt.objects.first()


def _dashboard_receipt_url(
    receipt_id: int,
    *,
    saved: bool = False,
    delete_error: bool = False,
) -> str:
    query = {"receipt": str(receipt_id)}
    if saved:
        query["saved"] = "1"
    if delete_error:
        query["delete_error"] = "1"
    return f"{reverse('receipts:dashboard')}?{urlencode(query)}#receipt-review"


def _image_url(receipt: Receipt) -> str:
    if not receipt.rustfs_path:
        return ""
    if receipt.pk is None:
        return ""
    return reverse("receipts:receipt_image", args=[receipt.pk])


def _thumbnail_url(receipt: Receipt) -> str:
    if not receipt.rustfs_path:
        return ""
    if receipt.pk is None:
        return ""
    return reverse("receipts:receipt_thumbnail", args=[receipt.pk])


def _thumbnail_key(key: str) -> str:
    path = PurePosixPath(key)
    return str(path.with_name(f"{path.stem}.thumb.jpg"))


def _build_thumbnail(file_bytes: bytes) -> bytes:
    with Image.open(BytesIO(file_bytes)) as image:
        thumbnail = ImageOps.exif_transpose(image)
        if thumbnail.mode != "RGB":
            thumbnail = thumbnail.convert("RGB")
        thumbnail.thumbnail(THUMBNAIL_MAX_SIZE)
        output = BytesIO()
        thumbnail.save(output, format="JPEG", quality=80, optimize=True)
        return output.getvalue()


def _is_missing_storage_object(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code", "")
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"404", "NoSuchKey", "NoSuchBucket"} or status == 404


def _decimal_or_none(value: str | None):
    if not value:
        return None
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _date_or_none(value: str | None) -> date | None:
    if not value:
        return None
    return parse_date(value)


def web_manifest(request):
    return JsonResponse(
        {
            "name": "Sales Tax Tracker",
            "short_name": "Sales Tax",
            "description": "Capture receipts and track year-to-date sales tax deductions.",
            "start_url": "/capture/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#f3f4f6",
            "theme_color": "#0c885f",
            "icons": [
                {
                    "src": "/static/pwa/icon.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                }
            ],
        }
    )


def service_worker(request):
    js = """
const CACHE_NAME = 'salt-helper-v7';
const NAVIGATION_TIMEOUT_MS = 2000;
const CORE_ASSETS = [
  '/capture/',
  '/manifest.json',
  '/static/theme.css',
  '/static/receipts/capture.js',
  '/static/receipts/capture.css',
  '/static/vendor/alpinejs/cdn.min.js',
  '/static/pwa/icon.svg',
];
const OFFLINE_NOT_READY_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Offline capture unavailable</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }
    body { background: #f3f4f6; color: #111827; }
    main { max-width: 34rem; margin: 15vh auto; background: white; }
    main { border-radius: 1rem; padding: 1.5rem; }
    main { box-shadow: 0 1rem 3rem rgb(15 23 42 / 0.12); }
    h1 { margin-top: 0; font-size: 1.35rem; }
    p { color: #4b5563; line-height: 1.5; }
  </style>
</head>
<body>
  <main>
    <h1>Offline capture is not ready.</h1>
    <p>
      Open this app once while connected to your server,
      then wait for "Offline ready".
    </p>
  </main>
</body>
</html>`;

function fetchWithTimeout(request, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(request, { cache: 'no-store', signal: controller.signal })
    .finally(() => clearTimeout(timeout));
}

async function cacheResponse(request, response) {
  if (response.ok) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
  }
  return response;
}

async function captureFallback() {
  const cached = await caches.match('/capture/');
  if (cached) return cached;
  return new Response(OFFLINE_NOT_READY_HTML, {
    status: 503,
    statusText: 'Offline capture unavailable',
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}

function refreshCaptureShell(event, request) {
  event.waitUntil(
    fetchWithTimeout(request, NAVIGATION_TIMEOUT_MS)
      .then((response) => (response.ok ? cacheResponse('/capture/', response) : null))
      .catch(() => null)
  );
}

async function handleNavigation(event, request, url) {
  if (url.origin !== self.location.origin) return fetch(request);
  if (url.pathname === '/capture/') {
    const cached = await caches.match('/capture/');
    if (cached) {
      refreshCaptureShell(event, request);
      return cached;
    }
  }

  try {
    const response = await fetchWithTimeout(request, NAVIGATION_TIMEOUT_MS);
    if (url.pathname === '/capture/' && response.ok) {
      return cacheResponse('/capture/', response);
    }
    if (response.status < 500) return response;
  } catch (error) {
    return captureFallback();
  }
  return captureFallback();
}

function refreshCachedRequest(event, request) {
  event.waitUntil(
    fetchWithTimeout(request, NAVIGATION_TIMEOUT_MS)
      .then((response) => (response.ok ? cacheResponse(request, response) : null))
      .catch(() => null)
  );
}

async function handleCachedGet(event, request, url) {
  const shouldCache =
    url.origin === self.location.origin &&
    (CORE_ASSETS.includes(url.pathname) || url.pathname.startsWith('/static/'));
  if (!shouldCache) return fetch(request);
  if (CORE_ASSETS.includes(url.pathname)) {
    const cached = await caches.match(request);
    if (cached) {
      refreshCachedRequest(event, request);
      return cached;
    }
  }
  try {
    const response = await fetchWithTimeout(request, NAVIGATION_TIMEOUT_MS);
    if (response.ok) await cacheResponse(request, response);
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    const pathCached = await caches.match(url.pathname);
    if (pathCached) return pathCached;
    return new Response('Offline', { status: 504, statusText: 'Offline' });
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(event, request, url));
    return;
  }
  event.respondWith(handleCachedGet(event, request, url));
});
""".strip()
    response = HttpResponse(js.encode(), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
