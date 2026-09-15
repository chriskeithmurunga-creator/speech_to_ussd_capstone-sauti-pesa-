"""Demo contacts for Sauti Pesa."""

import re


CONTACTS = {
    "john": "0712345678",
    "mary": "0798765432",
    "peter": "0711223344",
    "alice": "0700112233",
    "brian": "0722334455",
    "james": "0733445566",
    "susan": "0744556677",
}


def _clean_name(name):
    """Normalize a spoken contact name."""

    name = str(name or "").lower().strip()

    # Remove punctuation.
    name = re.sub(r"[^\w\s]", "", name)

    # Remove repeated spaces.
    name = re.sub(r"\s+", " ", name)

    return name


def resolve_contact(name):
    """Find a contact by name."""

    name = _clean_name(name)

    if name in CONTACTS:
        number = CONTACTS[name]

        return {
            "name": name.title(),
            "number": number,
            "found": True,
        }

    return {
        "name": name.title(),
        "number": None,
        "found": False,
    }


def confirm_contact(name, user_reply):
    """Confirm a contact before completing a transaction."""

    result = resolve_contact(name)

    if not result["found"]:
        return {
            "status": "not_found",
            "message": f"No contact found for '{result['name']}'.",
        }

    if user_reply is None:
        return {
            "status": "needs_confirmation",
            "message": (
                f"Is it {result['name']}, "
                f"{result['number']}?"
            ),
        }

    reply = str(user_reply).lower().strip()

    if reply in {"yes", "y", "ndio"}:
        return {
            "status": "confirmed",
            "number": result["number"],
            "name": result["name"],
            "message": (
                f"Confirmed. Sending to "
                f"{result['name']} ({result['number']})."
            ),
        }

    return {
        "status": "cancelled",
        "message": (
            "Okay, cancelled. "
            "Please specify the correct contact."
        ),
    }
