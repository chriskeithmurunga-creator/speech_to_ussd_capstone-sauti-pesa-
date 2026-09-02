CONTACTS = {
    "john": "0712345678",
    "mary": "0798765432",
    "peter": "0711223344",
}

def resolve_contact(name):
    name = name.lower().strip()

    if name in CONTACTS:
        number = CONTACTS[name]
        return {"name": name.title(), "number": number, "found": True}
    else:
        return {"name": name, "number": None, "found": False}
def confirm_contact(name, user_reply):
    result = resolve_contact(name)

    if not result["found"]:
        return {"status": "not_found", "message": f"No contact found for '{name}'."}

    if user_reply is None:
        return {"status": "needs_confirmation", "message": f"Is it {result['name']}, {result['number']}?"}

    if user_reply.lower().strip() == "yes":
        return {"status": "confirmed", "number": result["number"], "message": f"Confirmed. Sending to {result['name']} ({result['number']})."}
    else:
        return {"status": "cancelled", "message": "Okay, cancelled. Please specify the correct contact."}