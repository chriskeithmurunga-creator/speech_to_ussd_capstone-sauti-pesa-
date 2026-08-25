"""Tests for slot extraction module."""

from src.slots.extractor import extract_slots


def test_extract_amount():
    result = extract_slots("send 5000 shillings")
    assert "amount" in result
    assert result["amount"] == "5000"


def test_extract_phone():
    result = extract_slots("send to 255712345678")
    assert "phone" in result


def test_no_slots():
    result = extract_slots("hello")
    assert result == {}