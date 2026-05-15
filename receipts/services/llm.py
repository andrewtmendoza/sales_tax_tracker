from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = "\n".join(
    [
        (
            "You are a careful receipt OCR assistant. The image may be crinkled, folded, "
            "blurry, shadowed, rotated, partly cropped, or photographed at an angle."
        ),
        (
            "Use the visible text plus receipt layout cues to recover the most likely values, "
            "but never invent fields that are not reasonably supported by the image."
        ),
        "Return ONLY valid JSON with no commentary or markdown fences.",
        "",
        "Extraction rules:",
        (
            "- merchant_name: use the store or business name from the top/header of the "
            "receipt. Prefer the actual merchant over mall/location text, slogans, phone "
            "numbers, or street addresses."
        ),
        (
            "- transaction_date: return the purchase date in YYYY-MM-DD format when visible. "
            "Prefer the transaction/purchase date over print time, reorder date, or loyalty "
            "expiry dates."
        ),
        (
            "- total_amount: return the final amount charged for the transaction. Prefer "
            "lines like TOTAL, AMOUNT, BALANCE DUE, VISA/MC/AMEX, or card charge total. Do "
            "not use subtotal, item totals, tip-only amounts, or cash tendered unless they "
            "are clearly the final total."
        ),
        (
            "- sales_tax_amount: return only the explicit tax amount charged on the receipt. "
            "Look for lines such as TAX, SALES TAX, TAX AMT, TAXABLE TAX, or similar. Do "
            "not infer tax from subtotal and total; if tax is not explicitly visible, "
            "return null."
        ),
        (
            "- Dining and fast-food receipts are common. Menu items, modifiers, combo lines, "
            "order numbers, server names, and table numbers are not the merchant name."
        ),
        (
            "- For restaurant receipts with tip lines: if the receipt shows only a blank tip "
            "line or a tip suggestion, do not include a suggested or handwritten tip in "
            "total_amount unless the final charged total is explicitly printed."
        ),
        (
            "- For fast-food receipts, the final amount is often near labels like TOTAL, "
            "ORDER TOTAL, AMOUNT DUE, CARD, CREDIT, DEBIT, or CASH."
        ),
        (
            "- For restaurant receipts, sales tax may appear near subtotal/food/beverage "
            "lines. Service charges, surcharges, delivery fees, bag fees, and gratuity are "
            "not sales tax unless the receipt explicitly labels them as tax."
        ),
        (
            "- If multiple candidates exist, choose the one best supported by the receipt "
            "structure and nearby labels."
        ),
        "- If a field is unreadable or uncertain, use null instead of guessing.",
        "- Preserve cents to two decimal places when present.",
        "",
        "Required schema (use null when a value is not visible or reliable):",
        "{",
        '  "merchant_name": string,',
        '  "transaction_date": "YYYY-MM-DD",',
        '  "total_amount": number,',
        '  "sales_tax_amount": number',
        "}",
    ]
)


class LLMError(Exception):
    pass


@dataclass
class Extracted:
    merchant_name: str = ""
    transaction_date: date | None = None
    total_amount: Decimal | None = None
    sales_tax_amount: Decimal | None = None
    raw_response: dict[str, Any] | None = field(default=None)


def extract_from_image(image_bytes: bytes, content_type: str = "image/jpeg") -> Extracted:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:{content_type};base64,{b64}"
    body = {
        "model": settings.RECEIPT_LLM_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": EXTRACTION_PROMPT},
                    {"type": "input_image", "image_url": data_uri},
                ],
            }
        ],
    }
    try:
        response = requests.post(
            settings.RECEIPT_LLM_RESPONSES_URL,
            headers={"Authorization": f"Bearer {settings.RECEIPT_LLM_API_KEY}"},
            json=body,
            timeout=settings.RECEIPT_LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        content = _response_text(payload)
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise LLMError(f"Receipt LLM request failed: {exc}") from exc

    parsed = _parse_json(content)
    return Extracted(
        merchant_name=str(parsed.get("merchant_name") or "").strip(),
        transaction_date=_to_date(parsed.get("transaction_date")),
        total_amount=_to_decimal(parsed.get("total_amount")),
        sales_tax_amount=_to_decimal(parsed.get("sales_tax_amount")),
        raw_response=payload,
    )


def _parse_json(content: str) -> dict[str, Any]:
    text = content.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Invalid JSON from LLM: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise LLMError(f"Expected JSON object, got {type(data).__name__}")
    return data


def _response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") != "output_text":
                continue
            text = content.get("text")
            if isinstance(text, str):
                return text

    raise LLMError("Receipt LLM response did not include output text")


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        logger.warning("LLM returned unparseable date: %r", value)
        return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.warning("LLM returned unparseable decimal: %r", value)
        return None
