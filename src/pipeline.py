"""End-to-end pipeline: audio -> ASR -> normalize -> intent -> slots -> USSD."""

from src.audio.recorder import record_audio
from src.asr.whisper import transcribe
from src.preprocessing.normalizer import load_slang_dictionary, normalize_text, clean_asr_output
from src.intent.predict import predict_intent, load_model
from src.intent.features import extract_features
from src.slots.extractor import extract_slots
from src.ussd.generator import generate_response


def run_pipeline(audio_path, slang_dict_path, model_name="logistic_regression"):
    """Run the full speech-to-USSD pipeline."""
    # 1. Transcribe audio
    raw_text = transcribe(audio_path)

    # 2. Normalize text
    slang_dict = load_slang_dictionary(slang_dict_path)
    cleaned = clean_asr_output(raw_text)
    normalized = normalize_text(cleaned, slang_dict)

    # 3. Predict intent
    model = load_model(model_name)
    vectorizer = load_vectorizer()  # needs vectorizer saved during training
    intent, confidence = predict_intent(normalized, model, vectorizer)

    # 4. Extract slots
    slots = extract_slots(normalized, intent)

    # 5. Generate USSD response
    response = generate_response(intent, slots)

    return response


def load_vectorizer(path="models/vectorizer.pkl"):
    """Load the fitted TF-IDF vectorizer."""
    import joblib
    return joblib.load(path)
