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