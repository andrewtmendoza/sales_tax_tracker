from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404
from ninja import File, Router, Schema, Status
from ninja.files import UploadedFile

from receipts.models import Receipt
from receipts.services import ingest

IMAGE_FILE = File(...)


class ReceiptIn(Schema):
    file_hash: str
    rustfs_path: str = ""
    merchant_name: str = ""
    transaction_date: date | None = None
    total_amount: Decimal | None = None
    sales_tax_amount: Decimal | None = None


class ReceiptPatch(Schema):
    merchant_name: str | None = None
    transaction_date: date | None = None
    total_amount: Decimal | None = None
    sales_tax_amount: Decimal | None = None


class ReceiptOut(Schema):
    id: int
    file_hash: str
    rustfs_path: str
    merchant_name: str
    transaction_date: date | None
    total_amount: Decimal | None
    sales_tax_amount: Decimal | None


class DuplicateOut(Schema):
    detail: str
    existing: ReceiptOut


class ErrorOut(Schema):
    detail: str


class YTDOut(Schema):
    year: int
    total_sales_tax: Decimal
    receipt_count: int


router = Router(tags=["receipts"])


@router.get("/", response=list[ReceiptOut])
def list_receipts(request):
    return list(Receipt.objects.all())


@router.post("/", response={201: ReceiptOut, 409: DuplicateOut})
def create_receipt(request, payload: ReceiptIn):
    existing = Receipt.objects.filter(file_hash=payload.file_hash).first()
    if existing:
        return Status(
            409,
            DuplicateOut(detail="Receipt with this file_hash already exists.", existing=existing),
        )
    receipt = Receipt.objects.create(**payload.dict())
    return Status(201, receipt)


@router.post(
    "/upload",
    response={201: ReceiptOut, 400: ErrorOut, 409: DuplicateOut, 415: ErrorOut},
)
def upload_receipt(
    request,
    image: UploadedFile = IMAGE_FILE,
):
    content_type = (image.content_type or "").lower()
    if content_type not in settings.RECEIPT_ALLOWED_IMAGE_TYPES:
        return Status(415, ErrorOut(detail="Unsupported image type"))

    if image.size and image.size > settings.RECEIPT_MAX_UPLOAD_BYTES:
        return Status(400, ErrorOut(detail="Upload exceeds maximum receipt image size"))

    file_bytes = image.read()
    if not file_bytes:
        return Status(400, ErrorOut(detail="Empty upload"))

    try:
        result = ingest.ingest_image(file_bytes, content_type)
    except ingest.DuplicateReceipt as exc:
        return Status(
            409,
            DuplicateOut(detail="Receipt already uploaded.", existing=exc.existing),
        )
    return Status(201, result.receipt)


@router.get("/{receipt_id}", response=ReceiptOut)
def get_receipt(request, receipt_id: int):
    return get_object_or_404(Receipt, id=receipt_id)


@router.patch("/{receipt_id}", response=ReceiptOut)
def update_receipt(request, receipt_id: int, payload: ReceiptPatch):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(receipt, field, value)
    receipt.save()
    return receipt


@router.delete("/{receipt_id}", response={204: None})
def delete_receipt(request, receipt_id: int):
    receipt = get_object_or_404(Receipt, id=receipt_id)
    receipt.delete()
    return Status(204, None)


@router.get("/stats/ytd", response=YTDOut)
def ytd_stats(request, year: int | None = None):
    from django.utils import timezone

    target = year or timezone.now().year
    qs = Receipt.objects.filter(transaction_date__year=target)
    return YTDOut(
        year=target,
        total_sales_tax=Receipt.ytd_sales_tax(target),
        receipt_count=qs.count(),
    )
