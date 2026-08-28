"""End-to-end test of the speech-to-USSD pipeline."""

from src.preprocessing.normalizer import load_slang_dictionary, normalize_text, clean_asr_output
from src.intent.features import extract_features
from src.intent.train import train_all
from src.intent.predict import predict_intent, load_model
from src.slots.extractor import extract_slots
from src.ussd.generator import generate_response

import joblib
import os

print("=== Speech-to-USSD Pipeline Test ===\n")

# 1. Test normalizer
print("--- 1. Text Normalization ---")
slang_dict = load_slang_dictionary("data/slang_dictionary/swahili_slang_typos.csv")
print(f"  Slang entries loaded: {len(slang_dict)}")

text = "  NIKO  taka  send  5000  "
cleaned = clean_asr_output(text)
normalized = normalize_text(cleaned, slang_dict)
print(f"  Original:  '{text}'")
print(f"  Cleaned:   '{cleaned}'")
print(f"  Normalized:'{normalized}'")

# 2. Train intent classifier
print("\n--- 2. Train Intent Classifier ---")
samples = [
    ("check my balance", "check_balance"),
    ("how much money do i have", "check_balance"),
    ("show me my balance", "check_balance"),
    ("send 5000 to john", "send_money"),
    ("transfer 1000 to mary", "send_money"),
    ("send money to 255712345678", "send_money"),
    ("buy airtime 500", "airtime"),
    ("top up 1000", "airtime"),
    ("purchase airtime", "airtime"),
]
texts = [s[0] for s in samples]
labels = [s[1] for s in samples]

X, vectorizer = extract_features(texts)
# Split for train/val
X_train, y_train = X[:6], labels[:6]
X_val, y_val = X[6:], labels[6:]

train_all(X_train, y_train, X_val, y_val, "models/intent_classifier")

# Save vectorizer
os.makedirs("models", exist_ok=True)
joblib.dump(vectorizer, "models/vectorizer.pkl")

# 3. Predict intent
print("\n--- 3. Intent Prediction ---")
model = load_model("logistic_regression", "models/intent_classifier")
vectorizer = joblib.load("models/vectorizer.pkl")

test_phrases = [
    "check my balance",
    "send 5000 to john",
    "buy airtime",
]
for phrase in test_phrases:
    intent, confidence = predict_intent(phrase, model, vectorizer)
    slots = extract_slots(phrase, intent)
    response = generate_response(intent, slots)
    print(f"  Input: '{phrase}'")
    print(f"    Intent: {intent} (conf: {confidence:.2f})")
    print(f"    Slots:  {slots}")
    print(f"    USSD:   {response['ussd_menu']}")
    print()

print("=== Done! Pipeline works end-to-end ===")