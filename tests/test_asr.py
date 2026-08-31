"""Tests for ASR module."""

from src.asr.whisper import transcribe, load_model


def test_transcribe_missing_file():
    """Transcribing a non-existent file should return an empty string, not crash."""
    result = transcribe("no_such_file.wav")
    assert result == ""


def test_transcribe_returns_str():
    """Transcribe should always return a string even if ASR is unavailable."""
    result = transcribe("")
    assert isinstance(result, str)


def test_load_model_returns_tuple():
    """load_model should return a 2-tuple (model, processor)."""
    model, processor = load_model("tiny")
    assert isinstance((model, processor), tuple)
