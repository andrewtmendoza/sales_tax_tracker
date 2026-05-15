from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from receipts.models import Receipt
from receipts.services import llm, storage

logger = logging.getLogger(__name__)

class DuplicateReceipt(Exception):
    def __init__(self, existing: Receipt):
        super().__init__(f"Receipt with hash {existing.file_hash} already exists")
        self.existing = existing


@dataclass
class IngestResult:
    receipt: Receipt
    created: bool


def _extension_for(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/heic": "heic",
        "image/heif": "heif",
    }
    return mapping.get(content_type.lower(), "bin")


def ingest_image(
    file_bytes: bytes,
    content_type: str,
) -> IngestResult:
    actual_hash = hashlib.sha256(file_bytes).hexdigest()
    key = f"receipts/{actual_hash}.{_extension_for(content_type)}"

    existing = Receipt.objects.filter(file_hash=actual_hash).first()
    if existing:
        raise DuplicateReceipt(existing)

    try:
        with transaction.atomic():
            receipt = Receipt.objects.create(file_hash=actual_hash, rustfs_path=key)
    except IntegrityError as exc:
        existing = Receipt.objects.get(file_hash=actual_hash)
        raise DuplicateReceipt(existing) from exc

    try:
        storage.upload_image(file_bytes, key, content_type)
    except Exception:
        receipt.delete()
        raise

    extracted = None
    processing_error = ""
    try:
        extracted = llm.extract_from_image(file_bytes, content_type)
    except llm.LLMError as exc:
        logger.warning("LLM extraction failed for %s: %s", key, exc)
        processing_error = str(exc)

    receipt.merchant_name = extracted.merchant_name if extracted else ""
    receipt.transaction_date = extracted.transaction_date if extracted else None
    receipt.total_amount = extracted.total_amount if extracted else None
    receipt.sales_tax_amount = extracted.sales_tax_amount if extracted else None
    receipt.raw_llm_response = extracted.raw_response if extracted else None
    receipt.processing_error = processing_error
    receipt.save()

    return IngestResult(receipt=receipt, created=True)
