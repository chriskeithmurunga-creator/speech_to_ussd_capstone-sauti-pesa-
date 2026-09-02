"""Command-line interface for the speech-to-USSD system.

Modes:
    python main.py --record                   Speak a command -> run pipeline
    python main.py --audio <file.wav>         Run pipeline on an audio file
    python main.py --text "send 5000 to john" Run pipeline from raw text (no ASR)
    python main.py --traces                   List all saved traces
    python main.py --trace <run_id>           View one trace
    python main.py --serve                    Open the browser trace UI
"""

import argparse
import json


def cli():
    parser = argparse.ArgumentParser(description="Speech-to-USSD Pipeline")
    parser.add_argument("--audio", help="Path to audio file")
    parser.add_argument("--record", action="store_true", help="Record a voice command from the mic")
    parser.add_argument("--duration", type=int, default=5, help="Recording duration in seconds")
    parser.add_argument("--text", help="Run the pipeline from raw text (skips ASR)")
    parser.add_argument("--model", default="logistic_regression", help="Model name")
    parser.add_argument("--traces", action="store_true", help="List saved traces")
    parser.add_argument("--trace", help="View a saved trace by run id")
    parser.add_argument("--serve", action="store_true", help="Launch the browser trace UI")
    parser.add_argument("--port", type=int, default=8000, help="Port for --serve")
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    args = parser.parse_args()

    if args.serve:
        from app.server import serve
        serve(port=args.port)
        return

    if args.traces:
        from src.trace import list_traces
        traces = list_traces()
        if not traces:
            print("No traces yet. Run the pipeline first.")
            return
        for t in traces:
            print(f"{t['run_id']}  {t['timestamp']}  intent={t['intent']!r}  transcript={t['whisper_transcript'][:40]!r}")
        return

    if args.trace:
        from src.trace import get_trace
        trace = get_trace(args.trace)
        if trace is None:
            print(f"Trace not found: {args.trace}")
            return
        print(json.dumps(trace, indent=2, ensure_ascii=False))
        return

    if not args.audio and not args.record and not args.text:
        parser.error("Provide one of: --audio FILE, --record, --text TEXT, --traces, --trace ID, --serve")

    from src.pipeline import run_pipeline

    if args.text:
        result = run_pipeline(model_name=args.model, raw_text_override=args.text, source="text")
    elif args.record:
        result = run_pipeline(model_name=args.model, record_duration=args.duration, source="mic")
    else:
        result = run_pipeline(audio_path=args.audio, model_name=args.model, source="file")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("=" * 50)
    print(f"Run ID        : {result['run_id']}")
    print(f"Whisper text  : {result['whisper_transcript']!r}")
    print(f"Normalized    : {result['normalized_text']!r}")
    print(f"Intent        : {result['intent']} ({result['confidence']:.2f})")
    print(f"Slots         : {result['slots']}")
    print(f"USSD menu     : {result['ussd_menu']}")
    print(f"USSD sequence : {result['ussd_sequence']}")
    print("=" * 50)