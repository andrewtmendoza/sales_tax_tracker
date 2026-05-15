from django.contrib import admin

from receipts.models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "merchant_name",
        "transaction_date",
        "total_amount",
        "sales_tax_amount",
        "created_at",
    )
    search_fields = ("merchant_name", "file_hash")
    list_filter = ("transaction_date",)
    readonly_fields = ("file_hash", "rustfs_path", "raw_llm_response", "created_at", "updated_at")
