"""Audio recording module for capturing speech input."""


def record_audio(duration=5, sample_rate=16000):
    """Record audio from the microphone."""
    # Placeholder: actual implementation will use sounddevice or pyaudio
    print(f"Recording audio for {duration} seconds at {sample_rate} Hz...")
    return b""


def save_audio(audio_data, filepath):
    """Save recorded audio to a file."""
    with open(filepath, "wb") as f:
        f.write(audio_data)
    print(f"Audio saved to {filepath}")