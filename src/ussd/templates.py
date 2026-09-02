"""USSD menu templates for various services."""

MENU_TEMPLATES = {
    "check_balance": {
        "title": "Balance Inquiry",
        "body": "Your current balance is {balance} KSH.",
        "options": ["1. Back to Menu", "2. Exit"],
    },
    "send_money": {
        "title": "Send Money",
        "body": "Confirm: Send {amount} KSH to {recipient}?\n1. Yes\n2. No",
    },
    "airtime": {
        "title": "Buy Airtime",
        "body": "Enter amount:",
        "options": ["1. 500", "2. 1000", "3. 2000", "4. Other"],
    },
    "default": {
        "title": "Main Menu",
        "body": "Welcome to M-Pesa.\n1. Send Money\n2. Check Balance\n3. Buy Airtime\n4. Exit",
    },
}


def get_template(intent):
    """Get USSD template for given intent."""
    return MENU_TEMPLATES.get(intent, MENU_TEMPLATES["default"])


def render_template(intent, **kwargs):
    """Render a USSD template with provided slot values."""
    template = get_template(intent)
    body = template["body"].format(**kwargs)
    return template["title"], body
