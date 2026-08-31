"""End-to-end pipeline: audio -> ASR -> normalize -> intent -> slots -> USSD.

Every run is saved to data/traces/<run_id>/ so voice input is traceable:
audio.wav, whisper_transcript.txt, and trace.json (intent, slots, USSD).
"""

from pathlib import Path

from src.audio.recorder import save_audio, record_audio
from src.asr.whisper import transcribe
from src.intent.predict import predict_intent, load_model
from src.preprocessing.text_cleaner import clean_swahili_text
from src.slots.extractor import extract_slots
from src.ussd.generator import generate_response
from src.trace import save_trace, new_run_id

CACHE_AUDIO_DIR = Path("data/raw/recordings")


def load_vectorizer(path="models/vectorizer.pkl"):
    """Load the fitted TF-IDF vectorizer."""
    import joblib
    return joblib.load(path)


def run_pipeline(
    audio_path=None,
    slang_dict_path="data/slang_dictionary/swahili_slang_typos.csv",
    model_name="logistic_regression",
    source="file",
    raw_text_override=None,
    record_duration=5,
):
    """Run the full speech-to-USSD pipeline.

    - If audio_path is None, records from the microphone.
    - If raw_text_override is provided, skips ASR (useful for testing).
    """
    steps = []
    audio_path_saved = ""

    # 0. Capture audio (record or use provided file)
    if raw_text_override is None:
        if audio_path is None:
            audio_path_saved = str(
                CACHE_AUDIO_DIR / "recording_temp.wav"
            )
            audio_data = record_audio(duration=record_duration)
            save_audio(audio_data, audio_path_saved)
            source = "mic"
        else:
            audio_path_saved = str(audio_path)
        steps.append({"step": "audio", "value": audio_path_saved})

    # 1. Transcribe with Whisper
    if raw_text_override is not None:
        raw_transcript = raw_text_override
    else:
        raw_transcript = transcribe(audio_path_saved)
    steps.append({"step": "asr", "value": raw_transcript})

    # 2. Normalize text (uses Vivian's text_cleaner, no modifications)
    cleaned = clean_swahili_text(raw_transcript)
    steps.append({"step": "normalized_text", "value": cleaned})

    # 3. Predict intent
    model = load_model(model_name)
    vectorizer = load_vectorizer()
    intent, confidence = predict_intent(cleaned, model, vectorizer)
    steps.append({"step": "intent", "value": intent, "confidence": confidence})

    # 4. Extract slots
    slots = extract_slots(cleaned, intent)
    steps.append({"step": "slots", "value": slots})

    # 5. Generate USSD response
    response = generate_response(intent, slots)
    steps.append({"step": "ussd", "value": response["ussd_menu"]})

    run_id = new_run_id()
    save_trace(
        run_id,
        audio_path=audio_path_saved,
        raw_transcript=raw_transcript,
        normalized_text=cleaned,
        intent=intent,
        confidence=confidence,
        slots=slots,
        ussd_menu=response.get("ussd_menu", ""),
        ussd_sequence=response.get("ussd_sequence", ""),
        steps=steps,
        source=source,
    )

    result = {
        "run_id": run_id,
        "whisper_transcript": raw_transcript,
        "normalized_text": cleaned,
        "intent": intent,
        "confidence": confidence,
        "slots": slots,
        "ussd_menu": response.get("ussd_menu", ""),
        "ussd_sequence": response.get("ussd_sequence", ""),
        "steps": steps,
    }
    return result