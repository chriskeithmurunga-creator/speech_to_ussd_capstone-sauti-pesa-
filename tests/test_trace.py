"""Tests for the trace store."""

import json
import tempfile
from pathlib import Path

import src.trace as trace


def test_new_run_id_unique():
    a = trace.new_run_id()
    b = trace.new_run_id()
    assert a != b
    assert len(a) > 10


def test_save_and_get_trace(monkeypatch, tmp_path):
    # Redirect traces dir to a temp location to avoid polluting data/
    monkeypatch.setattr(trace, "TRACES_DIR", Path(tmp_path))

    audio_file = tmp_path / "in.wav"
    audio_file.write_bytes(b"\x00\x01\x02")

    trace.save_trace(
        "test-run-1",
        audio_path=str(audio_file),
        raw_transcript="tuma soo tano kwa mama",
        normalized_text="tuma soo tano kwa mama",
        intent="send_money",
        confidence=0.9,
        slots={"amount": "500", "recipient": "mama"},
        ussd_menu="Send 500 TZS to mama?",
        ussd_sequence="*334# -> 1 -> mama -> 500",
    )

    # Audio should have been copied into the trace dir
    assert (Path(tmp_path) / "test-run-1" / "audio.wav").exists()
    transcript_file = Path(tmp_path) / "test-run-1" / "whisper_transcript.txt"
    assert transcript_file.read_text() == "tuma soo tano kwa mama"

    data = trace.get_trace("test-run-1")
    assert data is not None
    assert data["intent"] == "send_money"
    assert data["slots"]["amount"] == "500"
    assert data["ussd_sequence"] == "*334# -> 1 -> mama -> 500"


def test_list_traces_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(trace, "TRACES_DIR", Path(tmp_path))
    assert trace.list_traces() == []


def test_get_missing_trace(monkeypatch, tmp_path):
    monkeypatch.setattr(trace, "TRACES_DIR", Path(tmp_path))
    assert trace.get_trace("nope") is None