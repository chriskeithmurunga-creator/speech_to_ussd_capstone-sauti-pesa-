"""Run-trace store: records every pipeline run so voice input is traceable.

Each run produces a directory:
    data/traces/<run_id>/
        audio.wav                 # original voice clip (if recorded/provided)
        whisper_transcript.txt    # raw Whisper transcript of the voice
        trace.json                # full step-by-step breakdown
"""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path("data/traces")


def new_run_id() -> str:
    """Generate a short timestamped run id, e.g. 20260830T203455-abc123."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ts}-{uuid.uuid4().hex[:6]}"


def save_trace(
    run_id: str,
    *,
    audio_path: str = "",
    raw_transcript: str = "",
    normalized_text: str = "",
    intent: str = "",
    confidence: float = 0.0,
    slots: dict = None,
    ussd_menu: str = "",
    ussd_sequence: str = "",
    steps: list = None,
    source: str = "file",
):
    """Save a run's artifacts into its trace directory. Returns the run dir."""
    trace_dir = TRACES_DIR / run_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Copy the source audio into the trace dir as audio.wav
    if audio_path and Path(audio_path).exists():
        dest = trace_dir / "audio.wav"
        try:
            shutil.copyfile(audio_path, dest)
        except OSError:
            pass

    transcript_file = trace_dir / "whisper_transcript.txt"
    transcript_file.write_text(raw_transcript or "", encoding="utf-8")

    trace = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "audio_path": str(trace_dir / "audio.wav"),
        "whisper_transcript": raw_transcript,
        "normalized_text": normalized_text,
        "intent": intent,
        "confidence": confidence,
        "slots": slots or {},
        "ussd_menu": ussd_menu,
        "ussd_sequence": ussd_sequence,
        "steps": steps or [],
    }
    (trace_dir / "trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return trace_dir


def list_traces() -> list[dict]:
    """Return metadata for all traces, newest first."""
    if not TRACES_DIR.exists():
        return []
    runs = []
    for trace_dir in sorted(TRACES_DIR.iterdir()):
        if not trace_dir.is_dir():
            continue
        trace_file = trace_dir / "trace.json"
        if not trace_file.exists():
            continue
        try:
            data = json.loads(trace_file.read_text(encoding="utf-8"))
            runs.append(
                {
                    "run_id": data.get("run_id", trace_dir.name),
                    "timestamp": data.get("timestamp", ""),
                    "intent": data.get("intent", ""),
                    "whisper_transcript": data.get("whisper_transcript", ""),
                    "source": data.get("source", ""),
                    "has_audio": (trace_dir / "audio.wav").exists(),
                }
            )
        except json.JSONDecodeError:
            continue
    runs.sort(key=lambda r: r["timestamp"], reverse=True)
    return runs


def get_trace(run_id: str) -> dict | None:
    """Return the full trace for a run id, or None."""
    trace_dir = TRACES_DIR / run_id
    trace_file = trace_dir / "trace.json"
    if not trace_file.exists():
        return None
    try:
        return json.loads(trace_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def trace_audio_path(run_id: str) -> Path:
    """Return the path to a trace's audio.wav (may not exist)."""
    return TRACES_DIR / run_id / "audio.wav"