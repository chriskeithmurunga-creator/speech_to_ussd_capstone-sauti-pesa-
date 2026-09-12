
"""Slot/entity extraction from user utterances."""

import re

# Reuse Vivian's slang/amount mapping (import only, no modification)
try:
    from src.preprocessing.text_cleaner import ACTIVE_SLANG_MAP
except ImportError:
    ACTIVE_SLANG_MAP = {}


# Simple keyword-based slot extraction
SLOT_PATTERNS = {
    "amount": r"(\d+[.,]?\d*)\s*(?:shillings?|ksh|tzs|usd)?",
    "phone": r"(\+?\d{9,13})",
    "account": r"(?:account\s*)?(\d{6,12})",
    "name": r"(?:to|for|kwa)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
}


# Sheng/Swahili spoken amount phrases
AMOUNT_PHRASES = [
    ("soo tano", "500"),
    ("soo mbili", "200"),
    ("soo moja", "100"),

    ("elfu moja", "1000"),
    ("elfu mbili", "2000"),
    ("elfu tatu", "3000"),
    ("elfu nne", "4000"),
    ("elfu tano", "5000"),
    ("elfu sita", "6000"),
    ("elfu saba", "7000"),
    ("elfu nane", "8000"),
    ("elfu tisa", "9000"),
    ("elfu kumi", "10000"),

    ("fifty bob", "50"),
    ("bob mbao", "20"),
    ("chapaa soo tano", "500"),
    ("punch", "100"),
    ("mbao", "20"),
]


def _normalize_amount(text: str) -> str:
    """Return a normalized numeric amount found in text, or ''."""

    word_to_num = {
        "fifty": "50",
        "hundred": "100",
        "five hundred": "500",
        "one thousand": "1000",
        "two thousand": "2000",
        "three thousand": "3000",
        "four thousand": "4000",
        "five thousand": "5000",
        "six thousand": "6000",
        "seven thousand": "7000",
        "eight thousand": "8000",
        "nine thousand": "9000",
        "ten thousand": "10000",
    }

    lower = text.lower()

    # Check Swahili/Sheng spoken amounts
    for phrase, num in AMOUNT_PHRASES:
        if phrase in lower:
            return num

    # Check English spoken amounts
    for phrase, num in word_to_num.items():
        if phrase in lower:
            return num

    # Check slang map for numeric values
    for key, val in ACTIVE_SLANG_MAP.items():
        if key in lower and re.fullmatch(r"\d+", val or ""):
            return val

    return ""


def extract_slots(text, intent=None):
    """Extract named entities/slots from user text."""

    slots = {}

    # Extract numeric slots
    for slot_name, pattern in SLOT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            slots[slot_name] = match.group(1)

    # If no numeric amount was found,
    # look for spoken/Sheng/Swahili amounts.
    if "amount" not in slots:
        spoken = _normalize_amount(text)

        if spoken:
            slots["amount"] = spoken

    # If we have a phone and no name,
    # use the phone number as the recipient.
    if "phone" in slots and "name" not in slots:
        slots["recipient"] = slots["phone"]

    # If we have a name, use the name as the recipient.
    elif "name" in slots:
        slots["recipient"] = slots["name"]

    return slots

