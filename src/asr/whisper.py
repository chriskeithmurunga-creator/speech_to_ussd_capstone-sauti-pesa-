"""Automatic Speech Recognition using Whisper (transformers).

Loads the fine-tuned checkpoint from models/whisper_finetuned/ if present,
otherwise falls back to the base openai/whisper-tiny model. If transformers
is not installed or no model is downloadable, gracefully returns an empty
string so the rest of the pipeline can still run.
"""

from functools import lru_cache
from pathlib import Path

FINETUNED_MODEL_DIR = Path("models/whisper_finetuned")
DEFAULT_MODEL = "openai/whisper-tiny"


@lru_cache(maxsize=1)
def load_model(model_size="tiny"):
    """Load a Whisper model, preferring the fine-tuned checkpoint.

    Returns (model, processor) or (None, None) if unavailable.
    """
    try:
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
    except ImportError:
        print("Warning: transformers not installed. Install to enable transcription.")
        return None, None

    if FINETUNED_MODEL_DIR.exists() and any(FINETUNED_MODEL_DIR.iterdir()):
        model_id = str(FINETUNED_MODEL_DIR)
        print(f"Loading fine-tuned Whisper from {model_id}")
    else:
        if model_size == "tiny":
            model_id = DEFAULT_MODEL
        else:
            model_id = f"openai/whisper-{model_size}"
        print(f"Loading base Whisper model: {model_id}")

    try:
        processor = WhisperProcessor.from_pretrained(model_id)
        model = WhisperForConditionalGeneration.from_pretrained(model_id)
        model.config.forced_decoder_ids = None
        model.config.suppress_tokens = []
    except Exception as e:
        print(f"Warning: could not load Whisper model {model_id}: {e}")
        return None, None

    return model, processor


def transcribe(audio_path, model_size="tiny", language="sw", task="transcribe"):
    """Transcribe audio file to text using Whisper.

    Returns the recognized text, or "" if ASR is unavailable.
    """
    model, processor = load_model(model_size)
    if model is None or processor is None:
        return ""

    import numpy as np
    import soundfile as sf

    try:
        audio, sr = sf.read(str(audio_path), dtype="float32")
    except Exception as e:
        print(f"Warning: could not read audio {audio_path}: {e}")
        return ""

    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        sr = 16000

    input_features = processor(audio, sampling_rate=sr, return_tensors="pt").input_features
    try:
        generated = model.generate(
            input_features,
            language=language,
            task=task,
        )
        text = processor.batch_decode(generated, skip_special_tokens=True)[0]
    except Exception as e:
        print(f"Warning: transcription failed: {e}")
        return ""

    return text.strip()
