from __future__ import annotations

from pathlib import PurePosixPath

from receipts.models import Receipt
from receipts.services import storage


def delete_receipt(receipt: Receipt) -> None:
    if receipt.rustfs_path:
        original_key = str(receipt.rustfs_path)
        storage.delete_image(original_key)
        storage.delete_image(_thumbnail_key(original_key))
    receipt.delete()


def _thumbnail_key(key: str) -> str:
    path = PurePosixPath(key)
    return str(path.with_name(f"{path.stem}.thumb.jpg"))
