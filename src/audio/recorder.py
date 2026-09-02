"""Audio recording module for capturing speech input.

Uses sounddevice to capture from the microphone, then writes a 16 kHz mono
16-bit PCM WAV using only the stdlib `wave` module.
"""

import wave
from pathlib import Path

SAMPLE_RATE = 16000


def record_audio(duration=5, sample_rate=SAMPLE_RATE, channels=1) -> bytes:
    """Record audio from the microphone and return the raw PCM bytes."""
    import sounddevice as sd

    print(f"Recording {duration}s at {sample_rate} Hz... speak now!")
    frames = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
    )
    sd.wait()
    return frames.tobytes()


def save_audio(audio_data: bytes, filepath, sample_rate=SAMPLE_RATE, channels=1) -> str:
    """Save raw int16 PCM bytes as a 16-bit mono WAV file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
    print(f"Audio saved to {filepath}")
    return str(filepath)
