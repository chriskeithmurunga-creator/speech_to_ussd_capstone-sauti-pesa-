"""Automatic Speech Recognition using Whisper (transformers).

Loads the fine-tuned checkpoint from models/whisper_finetuned/ if present,
otherwise falls back to the base openai/whisper-tiny model.

Browser WebM audio is converted to WAV using the FFmpeg executable
bundled with imageio-ffmpeg before Whisper processes it.
"""

from functools import lru_cache
from pathlib import Path
import tempfile
import subprocess

FINETUNED_MODEL_DIR = Path("models/whisper_finetuned")
DEFAULT_MODEL = "openai/whisper-tiny"


@lru_cache(maxsize=1)
def load_model(model_size="tiny"):
    """Load a Whisper model, preferring the fine-tuned checkpoint.

    Returns (model, processor) or (None, None) if unavailable.
    """
    try:
        from transformers import (
            WhisperForConditionalGeneration,
            WhisperProcessor,
        )
    except ImportError:
        print(
            "Warning: transformers not installed. "
            "Install to enable transcription."
        )
        return None, None

    if FINETUNED_MODEL_DIR.exists() and any(
        FINETUNED_MODEL_DIR.iterdir()
    ):
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
        model = WhisperForConditionalGeneration.from_pretrained(
            model_id
        )

        model.config.forced_decoder_ids = None
        model.config.suppress_tokens = []

    except Exception as e:
        print(
            f"Warning: could not load Whisper model "
            f"{model_id}: {e}"
        )
        return None, None

    return model, processor


def convert_to_wav(audio_path):
    """Convert an audio file to WAV using bundled FFmpeg.

    Returns the path to the converted WAV file.
    """
    from imageio_ffmpeg import get_ffmpeg_exe

    ffmpeg_exe = get_ffmpeg_exe()

    temp_wav = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False,
    )
    temp_wav.close()

    command = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(audio_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        temp_wav.name,
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )

    return Path(temp_wav.name)


def transcribe(
    audio_path,
    model_size="tiny",
    language="sw",
    task="transcribe",
):
    """Transcribe audio file to text using Whisper.

    Returns the recognized text, or "" if ASR is unavailable.
    """
    model, processor = load_model(model_size)

    if model is None or processor is None:
        return ""

    import soundfile as sf

    original_path = Path(audio_path)
    converted_path = None

    try:
        # Browser recordings are usually WebM.
        # Convert them to WAV before SoundFile tries to read them.
        if original_path.suffix.lower() in {
            ".webm",
            ".ogg",
            ".opus",
            ".m4a",
            ".mp4",
        }:
            try:
                converted_path = convert_to_wav(original_path)
                audio_file = converted_path
            except Exception as e:
                print(
                    f"Warning: could not convert audio "
                    f"{audio_path}: {e}"
                )
                return ""
        else:
            audio_file = original_path

        audio, sr = sf.read(
            str(audio_file),
            dtype="float32",
        )

    except Exception as e:
        print(
            f"Warning: could not read audio "
            f"{audio_path}: {e}"
        )
        return ""

    finally:
        if converted_path is not None:
            converted_path.unlink(missing_ok=True)

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if sr != 16000:
        import librosa

        audio = librosa.resample(
            audio,
            orig_sr=sr,
            target_sr=16000,
        )
        sr = 16000

    input_features = processor(
        audio,
        sampling_rate=sr,
        return_tensors="pt",
    ).input_features

    try:
        generated = model.generate(
            input_features,
            language=language,
            task=task,
        )

        text = processor.batch_decode(
            generated,
            skip_special_tokens=True,
        )[0]

    except Exception as e:
        print(
            f"Warning: transcription failed: {e}"
        )
        return ""

    return text.strip()