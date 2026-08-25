"""Tests for ASR module."""

from src.asr.whisper import transcribe, load_model


def test_transcribe():
    result = transcribe("test_audio.wav")
    assert isinstance(result, str)


def test_load_model():
    model = load_model("tiny")
    assert model is None