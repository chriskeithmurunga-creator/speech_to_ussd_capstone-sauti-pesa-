from contacts import confirm_contact
from src.ussd.generator import generate_response


def process_request(intent, amount=None, recipient_name=None, user_reply=None, service=None):
<<<<<<< HEAD
    

    intent = intent.lower()  # match teammate's lowercase intent keys

=======
   
    intent = intent.lower()  # match teammate's lowercase intent keys

>>>>>>> 2e67812dbd72b5d6839cf3a03f9cc08721616402
    slots = {
        "amount": amount,
        "service": service,
    }
<<<<<<< HEAD

    if intent in ("send_money", "sendmoney"):
        contact_result = confirm_contact(recipient_name, user_reply)

        if contact_result["status"] != "confirmed":
            return contact_result  # needs_confirmation / not_found / cancelled

        slots["recipient"] = contact_result["number"]
        return generate_response(intent, slots)

    # all other intents skip contact resolution entirely
    slots["recipient"] = recipient_name
    return generate_response(intent, slots)


if __name__ == "__main__":
    # Step 1: ask for confirmation
    result = process_request("SEND_MONEY", amount=500, recipient_name="John", user_reply=None)
    print(result)

    # Step 2: confirmed
    result2 = process_request("SEND_MONEY", amount=500, recipient_name="John", user_reply="yes")
    print(result2)

    # Step 3: no contact needed
    result3 = process_request("CHECK_BALANCE")
    print(result3)
=======

    if intent in ("send_money", "sendmoney"):
        contact_result = confirm_contact(recipient_name, user_reply)

        if contact_result["status"] != "confirmed":
            return contact_result  

        slots["recipient"] = contact_result["number"]
        return generate_response(intent, slots)

    # all other intents skip contact resolution entirely
    slots["recipient"] = recipient_name
    return generate_response(intent, slots)
>>>>>>> 2e67812dbd72b5d6839cf3a03f9cc08721616402

    # Step 4: pay bill, needs a service name
    result4 = process_request("PAY_BILL", amount=200, service="KPLC")
    print(result4)

