"""Generate USSD responses from intents and slots."""

# Real Safaricom *334# (M-PESA) menu sequences, mirroring synthetic dataset format
USSD_SEQUENCES = {
    "send_money": "*334# -> 1 -> {recipient} -> {amount}",
    "buy_airtime": "*334# -> 3 -> 1 -> {recipient} -> {amount}",
    "check_balance": "*334# -> 6 -> 1",
    "buy_bundles": "*334# -> 3 -> 2 -> {amount}",
    "pay_bill": "*334# -> 2 -> 1 -> {service} -> {recipient} -> {amount}",
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
    """Generate a structured USSD response including the *334# sequence."""
    slots = slots or {}
    response = {
        "intent": intent,
        "status": status,
        "slots": slots,
        "ussd_menu": None,
        "ussd_sequence": USSD_SEQUENCES.get(
            intent, "*334# -> 0"
        ).format(
            recipient=_recipient(slots),
            amount=_amount(slots),
            service=slots.get("service") or "[SERVICE]",
        ),
    }

    if intent == "check_balance":
        balance = slots.get("amount", "0")
        response["ussd_menu"] = f"Your current balance is {balance} TZS."
    elif intent in ("send_money", "sendmoney"):
        response["ussd_menu"] = (
            f"Send {_amount(slots)} TZS to {_recipient(slots)}?\n"
            "1. Yes\n2. No"
        )
    elif intent in ("buy_airtime", "airtime"):
        response["ussd_menu"] = "Buy Airtime\nEnter amount:"
    elif intent in ("buy_bundles", "bundles"):
        response["ussd_menu"] = f"Buy Bundles\nEnter amount ({_amount(slots)}):"
    elif intent in ("pay_bill", "paybill"):
        response["ussd_menu"] = (
            f"Pay Bill\nService: {slots.get('service', '[SERVICE]')}\n"
            f"Account: {_recipient(slots)}\nAmount: {_amount(slots)}"
        )
    else:
        response["ussd_menu"] = (
            "Welcome.\n1. Send Money\n2. Check Balance\n3. Buy Airtime\n4. Exit"
        )

    return response
