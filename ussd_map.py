from contacts import confirm_contact
from src.ussd.generator import generate_response


def process_request(intent, amount=None, recipient_name=None, user_reply=None, service=None):
   
    intent = intent.lower()  # match teammate's lowercase intent keys

    slots = {
        "amount": amount,
        "service": service,
    }

    if intent in ("send_money", "sendmoney"):
        contact_result = confirm_contact(recipient_name, user_reply)

        if contact_result["status"] != "confirmed":
            return contact_result  

        slots["recipient"] = contact_result["number"]
        return generate_response(intent, slots)

    # all other intents skip contact resolution entirely
    slots["recipient"] = recipient_name
    return generate_response(intent, slots)


