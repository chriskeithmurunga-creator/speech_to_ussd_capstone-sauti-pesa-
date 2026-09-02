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

# Sheng/spoken amount phrases that can't be captured by the numeric regex
AMOUNT_PHRASES = [
    ("soo tano", "500"),
    ("soo mbili", "200"),
    ("soo moja", "100"),
    ("elfu mbili", "2000"),
    ("elfu moja", "1000"),
    ("fifty bob", "50"),
    ("bob mbao", "20"),
    ("chapaa soo tano", "500"),
    ("punch", "100"),
    ("mbao", "20"),
]


def _normalize_amount(text: str) -> str:
    """Return a normalized numeric amount found in text, or ''."""
    # English/Swahili numerals like 'five hundred'
    word_to_num = {
        "fifty": "50", "hundred": "100", "five hundred": "500",
        "one thousand": "1000", "two thousand": "2000", "ten thousand": "10000",
    }
    lower = text.lower()
    for phrase, num in AMOUNT_PHRASES:
        if phrase in lower:
            return num
    for phrase, num in word_to_num.items():
        if phrase in lower:
            return num
    # Try ACTIVE_SLANG_MAP values that look like plain numbers (e.g. 'ganji'->'money' won't match)
    for key, val in ACTIVE_SLANG_MAP.items():
        if key in lower and re.fullmatch(r"\d+", val or ""):
            return val
    return ""


def extract_slots(text, intent=None):
    """Extract named entities/slots from user text."""
    slots = {}
    for slot_name, pattern in SLOT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            slots[slot_name] = match.group(1)

    # If no numeric amount was found, look for spoken/Sheng amounts
    if "amount" not in slots:
        spoken = _normalize_amount(text)
        if spoken:
            slots["amount"] = spoken

    # If we have a phone and no name, prefer phone as recipient alias
    if "phone" in slots and "name" not in slots:
        slots["recipient"] = slots["phone"]
    elif "name" in slots:
        slots["recipient"] = slots["name"]

    return slots
