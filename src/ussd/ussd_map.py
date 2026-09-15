"""Generate USSD responses from intents and slots."""

# M-Pesa USSD sequences used by the Sauti Pesa demo
USSD_SEQUENCES = {

    "SEND_MONEY": "*334# -> 1 -> {recipient} -> {amount}",

    "BUY_AIRTIME": "*334# -> 3 -> {amount}",

    "CHECK_BALANCE": "*334# -> 6 -> 1",

    "BUY_BUNDLES": "*544# -> {amount}",

    "PAY_BILL": "*334# -> 2 -> 1 -> {service} -> {recipient} -> {amount}",
}


def _recipient(slots):
    return (
        slots.get("recipient")
        or slots.get("name")
        or slots.get("phone")
        or "[RECIPIENT]"
    )


def _amount(slots):
    return slots.get("amount") or "[AMOUNT]"


def generate_response(intent, slots, status="success"):
    """Generate a structured USSD response."""
    slots = slots or {}

    # Normalize intent names so both uppercase and lowercase work
    intent_upper = str(intent).upper()

    response = {
        "intent": intent,
        "status": status,
        "slots": slots,
        "ussd_menu": None,
        "ussd_sequence": USSD_SEQUENCES.get(
            intent_upper,
            "*334# -> 0"
        ).format(
            recipient=_recipient(slots),
            amount=_amount(slots),
            service=slots.get("service") or "[SERVICE]",
        ),
    }

    if intent_upper == "CHECK_BALANCE":
        balance = slots.get("amount", "0")
        response["ussd_menu"] = f"Your current balance is KSh {balance}."

    elif intent_upper == "SEND_MONEY":
        response["ussd_menu"] = (
            f"Send KSh {_amount(slots)} to {_recipient(slots)}?\n"
            "1. Yes\n2. No"
        )

    elif intent_upper == "BUY_AIRTIME":
        response["ussd_menu"] = (
            f"Buy Airtime\n"
            f"Amount: KSh {_amount(slots)}"
        )

    elif intent_upper == "BUY_BUNDLES":
        response["ussd_menu"] = (
            f"Buy Bundles\n"
            f"Amount: KSh {_amount(slots)}"
        )

    elif intent_upper == "PAY_BILL":
        response["ussd_menu"] = (
            f"Pay Bill\n"
            f"Service: {slots.get('service', '[SERVICE]')}\n"
            f"Account: {_recipient(slots)}\n"
            f"Amount: KSh {_amount(slots)}"
        )

    else:
        response["ussd_menu"] = "Request received."

    return response
