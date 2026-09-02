"""Tests for slot extraction module."""

from src.slots.extractor import extract_slots


def test_extract_amount():
    result = extract_slots("send 5000 shillings")
    assert "amount" in result
    assert result["amount"] == "5000"


def test_extract_spoken_amount():
    """Sheng/spoken amounts should normalize to a number."""
    result = extract_slots("tuma soo tano kwa mama")
    assert result["amount"] == "500"


def test_extract_phone():
    result = extract_slots("send to 255712345678")
    assert "phone" in result


def test_extract_name_after_kwa():
    """Names after 'kwa' (Swahili for 'to') should be captured."""
    result = extract_slots("tuma elfu moja kwa mama")
    assert "name" in result
    assert result["name"] == "mama"


def test_extract_recipient_alias():
    """A name should be exposed as the recipient alias."""
    result = extract_slots("send 1000 to john")
    assert result["recipient"] == "john"


def test_no_slots():
    result = extract_slots("hello")
    assert result == {}
