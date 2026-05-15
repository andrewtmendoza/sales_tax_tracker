from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from receipts.models import Receipt
from receipts.services import storage


def dashboard(request):
    year = timezone.now().year
    selected_receipt = _selected_receipt(request.GET.get("receipt"))
    context = {
        "receipts": Receipt.objects.all(),
        "ytd_total": Receipt.ytd_sales_tax(year),
        "year": year,
        "selected_receipt": selected_receipt,
        "selected_image_url": _image_url(selected_receipt) if selected_receipt else "",
        "selected_saved": request.GET.get("saved") == "1",
    }
    return render(request, "receipts/dashboard.html", context)


def receipt_detail(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    if not getattr(request, "htmx", False):
        return redirect(_dashboard_receipt_url(receipt.id))
    return render(request, "receipts/_receipt_detail.html", _detail_context(receipt))


@require_POST
def receipt_update(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    receipt.merchant_name = request.POST.get("merchant_name", "").strip()
    receipt.transaction_date = request.POST.get("transaction_date") or None
    receipt.total_amount = _decimal_or_none(request.POST.get("total_amount"))
    receipt.sales_tax_amount = _decimal_or_none(request.POST.get("sales_tax_amount"))
    receipt.save()
    if not getattr(request, "htmx", False):
        return redirect(_dashboard_receipt_url(receipt.id, saved=True))
    return render(request, "receipts/_receipt_detail.html", _detail_context(receipt, saved=True))


def capture(request):
    return render(request, "receipts/capture.html", {})


def _detail_context(receipt: Receipt, saved: bool = False):
    return {
        "receipt": receipt,
        "image_url": _image_url(receipt),
        "saved": saved,
    }


def _selected_receipt(receipt_id: str | None):
    if receipt_id:
        try:
            return Receipt.objects.filter(id=int(receipt_id)).first() or Receipt.objects.first()
        except (TypeError, ValueError):
            pass
    return Receipt.objects.first()


def _dashboard_receipt_url(receipt_id: int, *, saved: bool = False) -> str:
    query = {"receipt": str(receipt_id)}
    if saved:
        query["saved"] = "1"
    return f"{reverse('receipts:dashboard')}?{urlencode(query)}#receipt-review"


def _image_url(receipt: Receipt) -> str:
    if not receipt.rustfs_path:
        return ""
    try:
        return storage.presigned_url(str(receipt.rustfs_path))
    except Exception:
        return ""


def _decimal_or_none(value: str | None):
    if not value:
        return None
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


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
            "theme_color": "#1f2937",
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
const CACHE_NAME = 'salt-helper-v3';
const CORE_ASSETS = [
  '/',
  '/capture/',
  '/manifest.json',
  '/static/receipts/capture.js',
  '/static/receipts/capture.css',
  '/static/vendor/alpinejs/cdn.min.js',
  '/static/pwa/icon.svg',
];

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
  const shouldCache =
    url.origin === self.location.origin &&
    (CORE_ASSETS.includes(url.pathname) || url.pathname.startsWith('/static/'));
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (shouldCache && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request).then((cached) => {
        if (cached) return cached;
        return caches.match(url.pathname).then((pathCached) => {
          if (pathCached) return pathCached;
          if (request.mode === 'navigate') {
            if (url.pathname === '/') return caches.match('/');
            return caches.match('/capture/');
          }
          return new Response('', { status: 504, statusText: 'Offline' });
        });
      }))
  );
});
""".strip()
    response = HttpResponse(js.encode(), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
