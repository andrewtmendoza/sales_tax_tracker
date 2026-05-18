from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Receipt(models.Model):
    objects = models.Manager()

    file_hash = models.CharField(max_length=64, unique=True, db_index=True)
    rustfs_path = models.CharField(max_length=512, blank=True, default="")

    merchant_name = models.CharField(max_length=255, blank=True, default="")
    transaction_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    sales_tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    raw_llm_response = models.JSONField(null=True, blank=True)
    processing_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-transaction_date", "-created_at")

    def __str__(self) -> str:
        return f"{self.merchant_name or 'Unknown'} — {self.transaction_date or 'pending'}"

    @classmethod
    def ytd_sales_tax(cls, year: int | None = None) -> Decimal:
        target_year = year or timezone.now().year
        result = cls.objects.filter(transaction_date__year=target_year).aggregate(
            total=Sum("sales_tax_amount")
        )
        total = result["total"] or Decimal("0.00")
        return total.quantize(Decimal("0.01"))
