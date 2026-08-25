"""Slot/entity extraction from user utterances."""

import re


# Simple keyword-based slot extraction
SLOT_PATTERNS = {
    "amount": r"(\d+[.,]?\d*)\s*(?:shillings?|ksh|tzs|usd)?",
    "phone": r"(\+?\d{10,13})",
    "account": r"(?:account\s*)?(\d{6,12})",
    "name": r"(?:name\s+(?:is\s+)?)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
}


def extract_slots(text, intent=None):
    """Extract named entities/slots from user text."""
    slots = {}
    for slot_name, pattern in SLOT_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            slots[slot_name] = match.group(1)
    return slots