"""Generate USSD responses from intents and slots."""


def generate_response(intent, slots, status="success"):
    """Generate a structured USSD response."""
    response = {
        "intent": intent,
        "status": status,
        "slots": slots,
        "ussd_menu": None,
    }

    if intent == "check_balance":
        balance = slots.get("amount", "0")
        response["ussd_menu"] = f"Your current balance is {balance} TZS."
    elif intent == "send_money":
        response["ussd_menu"] = (
            f"Send {slots.get('amount', '0')} TZS to {slots.get('phone', 'recipient')}?\n"
            "1. Yes\n2. No"
        )
    elif intent == "airtime":
        response["ussd_menu"] = "Buy Airtime\nEnter amount:"
    else:
        response["ussd_menu"] = (
            "Welcome.\n1. Send Money\n2. Check Balance\n3. Buy Airtime\n4. Exit"
        )

    return response