from contacts import confirm_contact
def build_ussd_string(intent, amount=None, number=None):
    if intent == "SEND_MONEY":
        return f"*334*1*{number}*{amount}#"

    elif intent == "PAY_BILL":
        return f"*334*3*{amount}#"

    elif intent == "CHECK_BALANCE":
        return "*334*4#"

    elif intent == "BUY_AIRTIME":
        return f"*544*{amount}#"

    elif intent == "BUY_BUNDLES":
        return f"*544*{amount}#"

    else:
        return "Unknown intent"


def process_request(intent, amount=None, recipient_name=None, user_reply=None):
    if intent == "SEND_MONEY":
        result = confirm_contact(recipient_name, user_reply)

        if result["status"] == "confirmed":
            return {"status": "ready", "ussd_string": build_ussd_string(intent, amount, result["number"])}
        else:
            return result  

    return {"status": "ready", "ussd_string": build_ussd_string(intent, amount)}

if __name__ == "__main__":
    result = process_request("SEND_MONEY", amount=500, recipient_name="John", user_reply=None)
    print(result)

    result2 = process_request("SEND_MONEY", amount=500, recipient_name="John", user_reply="yes")
    print(result2)

    result3 = process_request("CHECK_BALANCE")
    print(result3)


