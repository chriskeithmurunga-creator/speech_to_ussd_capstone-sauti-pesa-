import csv
import random
from pathlib import Path

# Spoken amount to normalized integer slot mapping
AMOUNT_NORM_MAP = {
    "soo tano": "500",
    "elfu moja": "1000",
    "fifty bob": "50",
    "bob mbao": "20",
    "soo mbili": "200",
    "elfu mbili": "2000",
    "punch": "100",
    "mbao": "20",
    "chapaa soo tano": "500",
    "Ksh 500": "500",
}

# Real Safaricom M-PESA *334# USSD Sequence Templates
USSD_MAPPINGS = {
    "SEND_MONEY": "*334# -> 1 -> {recipient} -> {amount}",
    "BUY_AIRTIME": "*334# -> 3 -> 1 -> {recipient} -> {amount}",
    "CHECK_BALANCE": "*334# -> 6 -> 1",
    "BUY_BUNDLES": "*334# -> 3 -> 2 -> {amount}",
    "PAY_BILL": "*334# -> 2 -> 1 -> {service} -> {recipient} -> {amount}",
}

TEMPLATES = {
    "SEND_MONEY": [
        "{action} {recipient} {amount_text}",
        "{action} {amount_text} kwa {recipient}",
        "Niaje {action} {amount_text} kwa {recipient}",
        "Tuma {amount_text} direct kwa {recipient}",
        "{action} cash {amount_text} hapa {recipient}",
        "Can you {action} {amount_text} to {recipient}",
        "Tuma Ksh {amount_num} to {recipient}",
        "Neelekeze {action} {amount_text} kwa {recipient}",
    ],
    "BUY_AIRTIME": [
        "{action} airtime ya {amount_text}",
        "{action} kredit {amount_text}",
        "Niongeze {amount_text} {recipient}",
        "Bao credit ya {amount_text} kwa {recipient}",
        "{action} {amount_text} airtime line hii",
        "Can I get {amount_text} airtime",
        "{action} kredit ya {amount_text} kwa number {recipient}",
    ],
    "CHECK_BALANCE": [
        "Check balance ya {service}",
        "Nionyeshe balance",
        "Nataka kuangalia balance kwa {service}",
        "Niambie salio langu la {service}",
        "How much money is in my {service}",
        "Check salio {service}",
        "Balance ni gani kwa {service}",
    ],
    "BUY_BUNDLES": [
        "Niongeze {service} za {amount_text}",
        "{action} data ya {amount_text}",
        "Nishikie bundles za {amount_text}",
        "Buy bundles za {amount_text} kwa {recipient}",
        "Nahitaji data bundles za {amount_text}",
        "Nipatie bundles ya {amount_text}",
    ],
    "PAY_BILL": [
        "Lipa bill ya {service} Ksh {amount_num}",
        "Paybill {service} amount {amount_num}",
        "{action} {service} soo {amount_num}",
        "Lipa {service} account {recipient} amount {amount_num}",
        "Lipia {service} elfu {amount_num}",
    ],
}

SLOT_VALUES = {
    "action": ["Nitumie", "Tuma", "Send", "Lipa", "Nishikie", "Weka", "Niletee"],
    "recipient": [
        "mama",
        "brathe",
        "sis",
        "0712345678",
        "0798765432",
        "0700112233",
        "chali yangu",
        "mzee",
        "shosh",
        "0722000000",
    ],
    "amount_text": [
        "soo tano",
        "elfu moja",
        "fifty bob",
        "bob mbao",
        "soo mbili",
        "elfu mbili",
        "punch",
        "mbao",
        "chapaa soo tano",
        "Ksh 500",
    ],
    "amount_num": ["50", "100", "200", "500", "1000", "1500", "2000", "5000"],
    "service": ["M-Pesa", "KPLC", "Zuku", "Safaricom", "net", "data", "token"],
}


def generate_synthetic_dataset(target_rows: int = 1000) -> list[dict]:
    dataset = []
    intents = list(TEMPLATES.keys())

    for i in range(target_rows):
        intent = intents[i % len(intents)]
        template = random.choice(TEMPLATES[intent])

        action = random.choice(SLOT_VALUES["action"])
        recipient_val = random.choice(SLOT_VALUES["recipient"])
        amount_text_val = random.choice(SLOT_VALUES["amount_text"])
        amount_num_val = random.choice(SLOT_VALUES["amount_num"])
        service_val = random.choice(SLOT_VALUES["service"])

        # Construct original transcript
        phrase = template.format(
            action=action,
            recipient=recipient_val,
            amount_text=amount_text_val,
            amount_num=amount_num_val,
            service=service_val,
        );3

        # Stage 5 Slot Extraction: Normalize slots into clean categorical values
        extracted_amount = ""
        if "{amount_num}" in template:
            extracted_amount = amount_num_val
        elif "{amount_text}" in template:
            extracted_amount = AMOUNT_NORM_MAP.get(
                amount_text_val, amount_text_val
            )

        extracted_recipient = recipient_val if "{recipient}" in template else ""
        extracted_service = service_val if "{service}" in template else ""

        # Format USSD sequence with extracted slot values
        ussd_seq = USSD_MAPPINGS[intent].format(
            recipient=extracted_recipient or "[RECIPIENT]",
            amount=extracted_amount or "[AMOUNT]",
            service=extracted_service or "[SERVICE]",
        )

        dataset.append({
            "id": f"syn_{i+1:04d}",
            "transcript": phrase,
            "intent": intent,
            "amount": extracted_amount,
            "recipient": extracted_recipient,
            "service": extracted_service,
            "ussd_sequence": ussd_seq,
            "is_synthetic": True,
        })

    random.shuffle(dataset)
    return dataset


def save_dataset(data: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "transcript",
        "intent",
        "amount",
        "recipient",
        "service",
        "ussd_sequence",
        "is_synthetic",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(
        f"Successfully generated and saved {len(data)} synthetic rows with extracted slots to {output_path}"
    )


if __name__ == "__main__":
    OUTPUT_FILE = Path("data/metadata/synthetic_intent_dataset.csv")
    synthetic_rows = generate_synthetic_dataset(target_rows=1000)
    save_dataset(synthetic_rows, OUTPUT_FILE)