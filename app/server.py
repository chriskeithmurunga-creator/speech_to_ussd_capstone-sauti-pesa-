"""Browser UI for browsing pipeline traces.

Runs a stdlib-only HTTP server (no FastAPI/Flask):
    GET  /                    -> trace list page
    GET  /trace/<run_id>      -> trace detail page with audio player + transcript
    GET  /audio/<run_id>      -> serves the recorded WAV for playback

Launch:  python -m app.server [--port 8000]
"""

import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.trace import list_traces, get_trace, trace_audio_path

TRACES_DIR = Path("data/traces")

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Speech-to-USSD — Voice Traces</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #222; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
tr:hover { background: #f5f5f5; }
code, pre { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
pre { padding: 12px; overflow-x: auto; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem; }
audio { width: 100%; margin: 8px 0; }
a { color: #06c; text-decoration: none; }
.muted { color: #777; }
.badge { display: inline-block; background: #eef; color: #336; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
</style>
</head>
<body>
"""

PAGE_FOOT = """</body>
</html>"""


def render_index() -> bytes:
    rows = list_traces()
    items = "\n".join(
        f"""<tr>
        <td><a href="/trace/{html.escape(t['run_id'])}">{html.escape(t['run_id'])}</a></td>
        <td>{html.escape(t['timestamp'])}</td>
        <td><span class="badge">{html.escape(t['intent'] or '—')}</span></td>
        <td class="muted">{html.escape(t['whisper_transcript'][:60])}</td>
        </tr>"""
        for t in rows
    )
    if not rows:
        items = '<tr><td colspan="4" class="muted">No traces yet. Run the pipeline (e.g. <code>python main.py --record</code>) to create one.</td></tr>'
    body = f"""
    <h1>🎙️ Speech-to-USSD — Voice Traces</h1>
    <p class="muted">Every run stores the audio clip + Whisper transcript + intent/slots/USSD output.</p>
    <table>
    <tr><th>Run ID</th><th>Timestamp</th><th>Intent</th><th>Whisper transcript</th></tr>
    {items}
    </table>
    """
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


def render_trace(run_id: str) -> bytes:
    trace = get_trace(run_id)
    if trace is None:
        return (PAGE_HEAD + f"<h1>Trace not found: {html.escape(run_id)}</h1><p><a href='/'>← Back</a></p>" + PAGE_FOOT).encode("utf-8")

    audio_html = ""
    if trace_audio_path(run_id).exists():
        audio_html = (
            f"<h3>🎧 Your voice clip</h3>"
            f"<audio controls preload='metadata'><source src='/audio/{html.escape(run_id)}' type='audio/wav'></audio>"
        )

    slots_json = json.dumps(trace.get("slots", {}), indent=2, ensure_ascii=False)
    body = f"""
    <p><a href="/">← All traces</a></p>
    <h1>Trace: {html.escape(run_id)}</h1>
    <p class="muted">{html.escape(trace.get('timestamp', ''))} · source: {html.escape(trace.get('source', ''))}</p>

    {audio_html}

    <div class="card">
      <h3>🗣️ Whisper transcript</h3>
      <pre>{html.escape(trace.get('whisper_transcript', ''))}</pre>
    </div>

    <div class="card">
      <h3>🧹 Normalized text</h3>
      <pre>{html.escape(trace.get('normalized_text', ''))}</pre>
    </div>

    <div class="card">
      <h3>🎯 Intent &amp; confidence</h3>
      <p><span class="badge">{html.escape(str(trace.get('intent', '')))}</span>
         {'{:.2f}'.format(trace.get('confidence', 0) or 0)}</p>
    </div>

    <div class="card">
      <h3>🧩 Extracted slots</h3>
      <pre>{html.escape(slots_json)}</pre>
    </div>

    <div class="card">
      <h3>📟 USSD menu</h3>
      <pre>{html.escape(trace.get('ussd_menu', ''))}</pre>
    </div>

    <div class="card">
      <h3>🔢 USSD sequence</h3>
      <pre>{html.escape(trace.get('ussd_sequence', ''))}</pre>
    </div>
    """
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


class TraceHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            content = render_index()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif path.startswith("/trace/"):
            run_id = path[len("/trace/"):]
            content = render_trace(run_id)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif path.startswith("/audio/"):
            run_id = path[len("/audio/"):]
            audio_path = trace_audio_path(run_id)
            if audio_path.exists():
                content = audio_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(content)))
            else:
                content = b"Audio not found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
        else:
            content = b"Not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")

        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args):
        print(f"[server] {self.address_string()} {fmt % args}")


def serve(port=8000, host="127.0.0.1"):
    server = ThreadingHTTPServer((host, port), TraceHandler)
    print(f"🌐 Trace UI running at http://{host}:{port}")
    print("   Open a browser to see traces and click a run to view its Whisper transcript.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Speech-to-USSD trace UI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    serve(port=args.port, host=args.host)