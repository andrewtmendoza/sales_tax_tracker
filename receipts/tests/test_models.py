from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from receipts.models import Receipt


@pytest.mark.django_db
def test_receipt_creates_with_required_hash():
    receipt = Receipt.objects.create(file_hash="a" * 64)
    assert receipt.id is not None
    assert receipt.file_hash == "a" * 64
    assert receipt.merchant_name == ""
    assert receipt.created_at is not None


@pytest.mark.django_db
def test_file_hash_is_unique():
    Receipt.objects.create(file_hash="b" * 64)
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        Receipt.objects.create(file_hash="b" * 64)


@pytest.mark.django_db
def test_ytd_sales_tax_sums_only_target_year():
    Receipt.objects.create(
        file_hash="1" * 64,
        transaction_date=date(2026, 1, 5),
        sales_tax_amount=Decimal("3.25"),
    )
    Receipt.objects.create(
        file_hash="2" * 64,
        transaction_date=date(2026, 6, 1),
        sales_tax_amount=Decimal("7.75"),
    )
    Receipt.objects.create(
        file_hash="3" * 64,
        transaction_date=date(2025, 12, 31),
        sales_tax_amount=Decimal("100.00"),
    )

    assert Receipt.ytd_sales_tax(2026) == Decimal("11.00")
    assert Receipt.ytd_sales_tax(2025) == Decimal("100.00")
    assert Receipt.ytd_sales_tax(2024) == Decimal("0.00")


@pytest.mark.django_db
def test_ytd_excludes_receipts_without_transaction_date():
    Receipt.objects.create(file_hash="9" * 64, sales_tax_amount=Decimal("50.00"))
    assert Receipt.ytd_sales_tax(2026) == Decimal("0.00")


@pytest.mark.django_db
def test_ytd_sales_tax_quantizes_decimal_sum_to_cents():
    Receipt.objects.create(
        file_hash="4" * 64,
        transaction_date=date(2026, 4, 18),
        sales_tax_amount=Decimal("4.26"),
    )
    Receipt.objects.create(
        file_hash="5" * 64,
        transaction_date=date(2026, 4, 12),
        sales_tax_amount=Decimal("9.66"),
    )
    Receipt.objects.create(
        file_hash="6" * 64,
        transaction_date=date(2026, 4, 8),
        sales_tax_amount=Decimal("2.96"),
    )

    assert Receipt.ytd_sales_tax(2026) == Decimal("16.88")
