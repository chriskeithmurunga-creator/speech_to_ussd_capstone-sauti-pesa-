"""Tests for USSD generation module."""

from src.ussd.generator import generate_response
from src.ussd.templates import get_template, render_template


def test_generate_balance():
    result = generate_response("check_balance", {"amount": "15000"})
    assert "balance" in result["ussd_menu"].lower()


def test_generate_default():
    result = generate_response("unknown", {})
    assert result["status"] == "success"


def test_get_template():
    template = get_template("airtime")
    assert "Enter amount" in template["body"]


def test_render_template():
    title, body = render_template("check_balance", balance="5000")
    assert "5000" in body


def test_send_money_uses_name():
    """Send-money menu should use the extracted recipient name."""
    result = generate_response("send_money", {"amount": "5000", "recipient": "john"})
    assert "john" in result["ussd_menu"]


def test_send_money_sequence():
    """Send-money should produce a *334# sequence mirroring the synthetic dataset."""
    result = generate_response("send_money", {"amount": "500", "recipient": "mama"})
    assert result["ussd_sequence"] == "*334# -> 1 -> mama -> 500"


def test_check_balance_sequence():
    result = generate_response("check_balance", {})
    assert result["ussd_sequence"] == "*334# -> 6 -> 1"
