from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import requests

from receipts.services import llm


def _mock_response(content: str, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"output_text": content, "id": "resp-test"}
    return resp


def _mock_nested_response(content: str):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "output": [
            {
                "type": "reasoning",
                "content": [
                    {"type": "reasoning_text", "text": "not the answer"},
                ]
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": content},
                ]
            }
        ],
        "id": "resp-nested-test",
    }
    return resp


def test_extract_from_image_parses_clean_json(mocker, settings):
    payload = {
        "merchant_name": "Trader Joe's",
        "transaction_date": "2026-05-12",
        "total_amount": 24.99,
        "sales_tax_amount": 2.03,
    }
    mock_post = mocker.patch(
        "receipts.services.llm.requests.post",
        return_value=_mock_response(json.dumps(payload)),
    )

    result = llm.extract_from_image(b"\xff\xd8fake", "image/jpeg")

    assert result.merchant_name == "Trader Joe's"
    assert result.transaction_date == date(2026, 5, 12)
    assert result.total_amount == Decimal("24.99")
    assert result.sales_tax_amount == Decimal("2.03")
    assert result.raw_response is not None
    assert result.raw_response["id"] == "resp-test"

    assert mock_post.call_args is not None
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == settings.RECEIPT_LLM_MODEL
    assert kwargs["json"]["input"][0]["content"][0]["type"] == "input_text"
    assert kwargs["json"]["input"][0]["content"][1]["type"] == "input_image"
    assert kwargs["json"]["input"][0]["content"][1]["image_url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert kwargs["timeout"] == settings.RECEIPT_LLM_TIMEOUT_SECONDS
    assert mock_post.call_args.args[0] == settings.RECEIPT_LLM_RESPONSES_URL


def test_extract_from_image_parses_nested_responses_output(mocker):
    content = (
        '{"merchant_name": "Nested", "transaction_date": null, "total_amount": null, '
        '"sales_tax_amount": 4.56}'
    )
    mocker.patch("receipts.services.llm.requests.post", return_value=_mock_nested_response(content))

    result = llm.extract_from_image(b"data", "image/jpeg")

    assert result.merchant_name == "Nested"
    assert result.sales_tax_amount == Decimal("4.56")


def test_extract_strips_markdown_fences(mocker):
    fenced = (
        '```json\n{"merchant_name": "Costco", "transaction_date": null, '
        '"total_amount": null, "sales_tax_amount": null}\n```'
    )
    mocker.patch("receipts.services.llm.requests.post", return_value=_mock_response(fenced))

    result = llm.extract_from_image(b"data", "image/jpeg")

    assert result.merchant_name == "Costco"
    assert result.transaction_date is None
    assert result.total_amount is None


def test_extract_tolerates_unparseable_date_and_decimal(mocker):
    payload = {
        "merchant_name": "Weird",
        "transaction_date": "not-a-date",
        "total_amount": "abc",
        "sales_tax_amount": "1.23",
    }
    mocker.patch(
        "receipts.services.llm.requests.post",
        return_value=_mock_response(json.dumps(payload)),
    )

    result = llm.extract_from_image(b"data", "image/jpeg")

    assert result.merchant_name == "Weird"
    assert result.transaction_date is None
    assert result.total_amount is None
    assert result.sales_tax_amount == Decimal("1.23")


def test_extract_raises_on_invalid_json(mocker):
    mocker.patch(
        "receipts.services.llm.requests.post",
        return_value=_mock_response("not json at all"),
    )
    with pytest.raises(llm.LLMError):
        llm.extract_from_image(b"data", "image/jpeg")


def test_extract_raises_on_request_failure(mocker):
    mocker.patch(
        "receipts.services.llm.requests.post",
        side_effect=requests.ConnectionError("down"),
    )
    with pytest.raises(llm.LLMError):
        llm.extract_from_image(b"data", "image/jpeg")
