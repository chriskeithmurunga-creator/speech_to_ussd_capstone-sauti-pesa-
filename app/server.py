"""Browser UI for running and browsing pipeline traces.

Runs a stdlib-only HTTP server (no FastAPI/Flask):
    GET  /                    -> trace list + "run a command" form
    POST /run                 -> runs the pipeline on submitted text, redirects to trace
    GET  /trace/<run_id>      -> trace detail page with audio player + pipeline stages
    GET  /audio/<run_id>      -> serves the recorded WAV for playback

Launch:  python -m app.server [--port 8000]
"""

import argparse
import html
import json
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from src.trace import list_traces, get_trace, trace_audio_path

TRACES_DIR = Path("data/traces")
UPLOADS_DIR = Path("data/raw/uploads")


def parse_multipart(body: bytes, content_type: str) -> dict:
    """Minimal multipart/form-data parser (stdlib only, no cgi module).

    Returns {field_name: {"content": bytes, "filename": str|None}} for file
    fields and {field_name: {"content": str, "filename": None}} for plain
    text fields. Good enough for this dashboard's forms; not general-purpose.
    """
    if "boundary=" not in content_type:
        return {}
    boundary = content_type.split("boundary=")[-1].strip().strip('"').encode("utf-8")
    delimiter = b"--" + boundary
    parts = body.split(delimiter)
    fields = {}
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        headers_blob, content = part.split(b"\r\n\r\n", 1)
        content = content.rstrip(b"\r\n")
        headers_text = headers_blob.decode("utf-8", errors="replace")
        name = None
        filename = None
        for header_line in headers_text.split("\r\n"):
            if header_line.lower().startswith("content-disposition:"):
                for chunk in header_line.split(";"):
                    chunk = chunk.strip()
                    if chunk.startswith("name="):
                        name = chunk[len("name="):].strip('"')
                    elif chunk.startswith("filename="):
                        filename = chunk[len("filename="):].strip('"')
        if name:
            fields[name] = {"content": content, "filename": filename or None}
    return fields

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sema, Tuma — Speech-to-USSD</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#1E4A3E">
<link rel="icon" href="/static/icon-192.png">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --paper: #F6F3EC;
    --ink: #1C2333;
    --ink-soft: #565F76;
    --line: #DAD4C4;
    --teal: #2F6E5C;
    --teal-deep: #1E4A3E;
    --ochre: #C98A2C;
    --screen-bg: #16241D;
    --screen-fg: #8FE3B8;
  }
  * { box-sizing: border-box; }
  body {
    font-family: "IBM Plex Sans", system-ui, sans-serif;
    background: var(--paper);
    color: var(--ink);
    max-width: 760px;
    margin: 0 auto;
    padding: 3rem 1.5rem 5rem;
    line-height: 1.5;
  }
  h1, h2, h3 { font-family: "Space Grotesk", sans-serif; font-weight: 700; margin: 0; }
  h1 { font-size: 1.9rem; letter-spacing: -0.01em; }
  .tagline { color: var(--ink-soft); margin: 0.4rem 0 2.5rem; max-width: 46ch; }
  a { color: var(--teal-deep); text-decoration: none; border-bottom: 1px solid transparent; }
  a:hover { border-bottom-color: var(--teal-deep); }

  /* --- run form --- */
  .run-panel {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1.5rem 1.6rem;
    margin-bottom: 2.8rem;
  }
  .run-panel h2 { font-size: 1.05rem; margin-bottom: 0.9rem; }
  .run-row { display: flex; gap: 0.6rem; }
  .run-row input[type=text] {
    flex: 1;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.95rem;
    padding: 0.7rem 0.85rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  .run-row input[type=text]:focus { outline: 2px solid var(--teal); outline-offset: 1px; }
  .run-row button {
    font-family: "Space Grotesk", sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    background: var(--teal-deep);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0 1.3rem;
    cursor: pointer;
  }
  .run-row button:hover { background: var(--teal); }
  .run-hint { color: var(--ink-soft); font-size: 0.85rem; margin: 0.7rem 0 0; }
  .run-hint code { background: var(--paper); border: 1px solid var(--line); padding: 1px 5px; border-radius: 4px; }
  .divider { display: flex; align-items: center; gap: 0.8rem; margin: 1.3rem 0; color: var(--ink-soft); font-size: 0.8rem; }
  .divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: var(--line); }
  .upload-row { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }
  .upload-row input[type=file] {
    flex: 1;
    min-width: 180px;
    font-size: 0.85rem;
    padding: 0.5rem;
    border: 1px dashed var(--line);
    border-radius: 6px;
    background: var(--paper);
  }
  .upload-row button {
    font-family: "Space Grotesk", sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    background: var(--ochre);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0.65rem 1.1rem;
    cursor: pointer;
    white-space: nowrap;
  }
  .upload-row button:hover { filter: brightness(0.92); }
  .upload-row select {
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 0.88rem;
    padding: 0.55rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
  }
  .record-btn { background: var(--teal-deep); }
  .record-btn:hover { background: var(--teal); filter: none; }

  .speak-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    width: 100%;
    padding: 1.1rem;
    font-family: "Space Grotesk", sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    background: var(--teal-deep);
    color: #fff;
    border: none;
    border-radius: 10px;
    cursor: pointer;
  }
  .speak-btn:hover { background: var(--teal); }
  .speak-btn.recording { background: var(--ochre); animation: pulse 1.4s infinite; }
  .speak-btn:disabled { opacity: 0.6; cursor: default; animation: none; }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(201, 138, 44, 0.45); }
    50% { box-shadow: 0 0 0 10px rgba(201, 138, 44, 0); }
  }

  /* --- trace table --- */
  table { border-collapse: collapse; width: 100%; }
  th { text-align: left; font-family: "Space Grotesk", sans-serif; font-size: 0.8rem; color: var(--ink-soft); font-weight: 500; padding: 0 8px 8px; border-bottom: 1px solid var(--line); }
  td { padding: 10px 8px; border-bottom: 1px solid var(--line); font-size: 0.92rem; }
  tr:hover td { background: #fff; }
  .empty-row td { color: var(--ink-soft); font-style: italic; }
  .badge {
    display: inline-block;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.78rem;
    background: #E4EFEA;
    color: var(--teal-deep);
    padding: 2px 9px;
    border-radius: 999px;
  }

  /* --- trace detail --- */
  .back { display: inline-block; margin-bottom: 1.6rem; font-size: 0.9rem; }
  .run-meta { color: var(--ink-soft); font-size: 0.88rem; margin: -0.3rem 0 1.6rem; }

  .phone {
    width: 220px;
    margin: 0 auto 2.2rem;
    background: var(--screen-bg);
    border-radius: 18px;
    padding: 18px 16px 20px;
  }
  .phone .label { color: #6FAE8C; font-size: 0.68rem; font-family: "IBM Plex Mono", monospace; letter-spacing: 0.04em; margin-bottom: 8px; }
  .phone .readout {
    font-family: "IBM Plex Mono", monospace;
    color: var(--screen-fg);
    font-size: 1.15rem;
    line-height: 1.5;
    min-height: 2.4em;
    word-break: break-all;
  }

  .stage {
    display: grid;
    grid-template-columns: 28px 1fr;
    gap: 0 14px;
    margin-bottom: 0;
  }
  .stage .dot-col { display: flex; flex-direction: column; align-items: center; }
  .stage .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--teal); margin-top: 6px; flex-shrink: 0; }
  .stage .stem { width: 1px; flex: 1; background: var(--line); margin-top: 2px; }
  .stage:last-child .stem { display: none; }
  .stage-body { padding-bottom: 1.6rem; }
  .stage-body h3 { font-size: 0.95rem; margin-bottom: 0.35rem; }
  .stage-body pre {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.85rem;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 10px 12px;
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .conf { color: var(--ochre); font-family: "IBM Plex Mono", monospace; font-size: 0.85rem; }

  audio { width: 100%; margin: 0.3rem 0 0; }

  .dial-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    width: 100%;
    margin-top: 12px;
    padding: 0.85rem 1rem;
    background: var(--teal);
    color: #fff;
    font-family: "Space Grotesk", sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    border-radius: 8px;
    border-bottom: none;
  }
  .dial-btn:hover { background: var(--teal-deep); border-bottom: none; }
  .dial-hint { text-align: center; color: var(--ink-soft); font-size: 0.78rem; margin: 6px 0 0; }

  @media (max-width: 540px) {
    body { padding: 1.4rem 1rem 3.5rem; }
    h1 { font-size: 1.5rem; }
    .tagline { margin-bottom: 1.8rem; }
    .run-panel { padding: 1.1rem 1.1rem; margin-bottom: 1.8rem; }
    .run-row { flex-direction: column; }
    .run-row button { padding: 0.75rem; }
    .upload-row { flex-direction: column; align-items: stretch; }
    .upload-row select { width: 100%; }
    table, thead, tbody, tr { display: block; }
    thead { display: none; }
    tr { border-bottom: 1px solid var(--line); padding: 10px 0; }
    tr.empty-row { border-bottom: none; }
    td { display: block; border-bottom: none; padding: 2px 0; }
    td:first-child { font-family: "IBM Plex Mono", monospace; font-size: 0.8rem; color: var(--ink-soft); }
    .phone { width: 100%; max-width: 260px; }
    .stage-body pre { font-size: 0.8rem; }
  }
</style>
</head>
<body>
"""

PAGE_FOOT = """</body>
</html>"""


def render_index(error: str | None = None) -> bytes:
    rows = list_traces()
    items = "\n".join(
        f"""<tr>
        <td><a href="/trace/{html.escape(t['run_id'])}">{html.escape(t['run_id'])}</a></td>
        <td>{html.escape(t['timestamp'])}</td>
        <td><span class="badge">{html.escape(t['intent'] or '—')}</span></td>
        <td>{html.escape(t['whisper_transcript'][:60])}</td>
        </tr>"""
        for t in rows
    )
    if not rows:
        items = '<tr class="empty-row"><td colspan="4">No runs yet — try one above, or run <code>python main.py --record</code> from the command line.</td></tr>'

    error_html = f'<p class="run-hint" style="color:#B3401F;">{html.escape(error)}</p>' if error else ""

    body = f"""
    <h1>Sema, Tuma</h1>
    <p class="tagline">Speak a request in Swahili, English or Sheng — watch it become a USSD sequence.</p>

    <div class="run-panel">
      <h2>Speak your command</h2>
      <button type="button" id="speakBtn" class="speak-btn">
        <span id="speakIcon">🎤</span> <span id="speakLabel">Tap to speak</span>
      </button>
      <p id="speakStatus" class="run-hint">Records on this device, then runs it through the full pipeline.</p>
      <p id="speakError" class="run-hint" style="color:#B3401F; display:none;"></p>

      <div class="divider"><span>or type it</span></div>

      <form class="run-row" action="/run" method="POST">
        <input type="text" name="text" placeholder="Nataka kutuma shilingi mia tano kwa John">
        <button type="submit">Run</button>
      </form>
      {error_html}
    </div>

    <div class="run-panel">
      <h2>Other ways to test</h2>
      <form class="upload-row" action="/run-audio" method="POST" enctype="multipart/form-data">
        <input type="file" name="audio" accept="audio/*" required>
        <button type="submit">Run on audio file</button>
      </form>
      <p class="run-hint">Upload an existing voice clip (.wav, .mp3, .m4a).</p>

      <div class="divider"><span>or</span></div>

      <form class="upload-row" action="/run-record" method="POST">
        <select name="duration">
          <option value="3">3s</option>
          <option value="5" selected>5s</option>
          <option value="8">8s</option>
        </select>
        <button type="submit" class="record-btn">Record on this computer</button>
      </form>
      <p class="run-hint">Uses the microphone on the machine <em>running the server</em> — not this device.</p>
    </div>

    <table>
    <tr><th>Run</th><th>Time</th><th>Intent</th><th>Transcript</th></tr>
    {items}
    </table>

    <script>
    (function () {{
      const btn = document.getElementById('speakBtn');
      const icon = document.getElementById('speakIcon');
      const label = document.getElementById('speakLabel');
      const status = document.getElementById('speakStatus');
      const errorEl = document.getElementById('speakError');
      let audioCtx, source, processor, stream, recording = false;
      let samples = [];
      let inputSampleRate = 44100;
      const TARGET_RATE = 16000;

      function showError(msg) {{
        errorEl.textContent = msg;
        errorEl.style.display = 'block';
      }}

      // Downsample Float32 PCM to 16kHz mono using simple linear interpolation.
      function downsample(buffer, fromRate, toRate) {{
        if (toRate >= fromRate) return buffer;
        const ratio = fromRate / toRate;
        const newLength = Math.round(buffer.length / ratio);
        const result = new Float32Array(newLength);
        for (let i = 0; i < newLength; i++) {{
          result[i] = buffer[Math.floor(i * ratio)];
        }}
        return result;
      }}

      // Encode Float32 PCM samples as a 16-bit mono WAV file (RIFF header).
      function encodeWav(float32Samples, sampleRate) {{
        const buffer = new ArrayBuffer(44 + float32Samples.length * 2);
        const view = new DataView(buffer);
        function writeString(offset, str) {{
          for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
        }}
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + float32Samples.length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);   // PCM
        view.setUint16(22, 1, true);   // mono
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);  // 16-bit
        writeString(36, 'data');
        view.setUint32(40, float32Samples.length * 2, true);
        let offset = 44;
        for (let i = 0; i < float32Samples.length; i++, offset += 2) {{
          const s = Math.max(-1, Math.min(1, float32Samples[i]));
          view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }}
        return new Blob([buffer], {{ type: 'audio/wav' }});
      }}

      async function stopAndSend() {{
        recording = false;
        icon.textContent = '🎤';
        label.textContent = 'Tap to speak';
        btn.classList.remove('recording');
        btn.disabled = true;
        status.textContent = 'Running the pipeline…';

        processor.disconnect();
        source.disconnect();
        stream.getTracks().forEach((t) => t.stop());
        audioCtx.close();

        let flat = new Float32Array(samples.reduce((n, c) => n + c.length, 0));
        let off = 0;
        for (const chunk of samples) {{ flat.set(chunk, off); off += chunk.length; }}
        const resampled = downsample(flat, inputSampleRate, TARGET_RATE);
        const wavBlob = encodeWav(resampled, TARGET_RATE);

        const formData = new FormData();
        formData.append('audio', wavBlob, 'recording.wav');

        try {{
          const resp = await fetch('/run-audio', {{ method: 'POST', body: formData }});
          if (resp.ok) {{
            window.location = resp.url;
          }} else {{
            status.textContent = '';
            showError('Pipeline error while processing your recording. Check the server logs.');
            btn.disabled = false;
          }}
        }} catch (err) {{
          status.textContent = '';
          showError('Could not reach the server to run the pipeline.');
          btn.disabled = false;
        }}
      }}

      btn.addEventListener('click', async function () {{
        if (recording) {{
          stopAndSend();
          return;
        }}
        errorEl.style.display = 'none';

        if (!navigator.mediaDevices || !(window.AudioContext || window.webkitAudioContext)) {{
          showError('This browser does not support in-page microphone recording. Try Chrome or Firefox, or use "Run on audio file" below.');
          return;
        }}

        try {{
          stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        }} catch (err) {{
          showError('Microphone access was blocked or unavailable. Note: on a phone, this needs an https:// address (not a plain http:// LAN address) unless you are on "localhost".');
          return;
        }}

        const AC = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AC();
        inputSampleRate = audioCtx.sampleRate;
        source = audioCtx.createMediaStreamSource(stream);
        processor = audioCtx.createScriptProcessor(4096, 1, 1);
        samples = [];

        processor.onaudioprocess = (e) => {{
          samples.push(new Float32Array(e.inputBuffer.getChannelData(0)));
        }};
        source.connect(processor);
        processor.connect(audioCtx.destination);

        recording = true;
        icon.textContent = '⏹';
        label.textContent = 'Tap to stop';
        btn.classList.add('recording');
        status.textContent = 'Listening… speak now.';

        setTimeout(() => {{ if (recording) stopAndSend(); }}, 20000);
      }});
    }})();
    </script>
    """
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


def render_trace(run_id: str) -> bytes:
    trace = get_trace(run_id)
    if trace is None:
        body = f"<a class='back' href='/'>&larr; All runs</a><h1>Run not found</h1><p>{html.escape(run_id)}</p>"
        return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")

    audio_html = ""
    if trace_audio_path(run_id).exists():
        audio_html = (
            f"<audio controls preload='metadata'>"
            f"<source src='/audio/{html.escape(run_id)}' type='audio/wav'></audio>"
        )

    slots_json = json.dumps(trace.get("slots", {}), indent=2, ensure_ascii=False)
    confidence = trace.get("confidence", 0) or 0
    ussd_sequence = trace.get("ussd_sequence", "")

    # Build a tel: URI so tapping it opens the phone dialer pre-filled with
    # the USSD code (works on Android; iOS restricts auto-dialing USSD for
    # security reasons and will show the code but may not auto-send it).
    # '#' must be percent-encoded in a tel: URI.
    dial_html = ""
    if ussd_sequence.strip():
        dial_target = ussd_sequence.strip().replace("#", "%23")
        dial_html = (
            f"<a class='dial-btn' href='tel:{html.escape(dial_target)}'>Dial this on your phone</a>"
            f"<p class='dial-hint'>Opens your phone dialer with the code pre-filled. Android only — "
            f"iOS blocks auto-dialing USSD codes.</p>"
        )

    stages = [
        ("Whisper transcript", f"<pre>{html.escape(trace.get('whisper_transcript', '') or '—')}</pre>{audio_html}"),
        ("Normalized text", f"<pre>{html.escape(trace.get('normalized_text', '') or '—')}</pre>"),
        ("Intent", f"<span class='badge'>{html.escape(str(trace.get('intent', '') or '—'))}</span> <span class='conf'>{confidence:.2f} confidence</span>"),
        ("Extracted slots", f"<pre>{html.escape(slots_json)}</pre>"),
        ("USSD menu", f"<pre>{html.escape(trace.get('ussd_menu', '') or '—')}</pre>"),
    ]

    stage_html = "\n".join(
        f"""<div class="stage">
          <div class="dot-col"><div class="dot"></div><div class="stem"></div></div>
          <div class="stage-body"><h3>{html.escape(title)}</h3>{content}</div>
        </div>"""
        for title, content in stages
    )

    body = f"""
    <a class="back" href="/">&larr; All runs</a>
    <h1>{html.escape(run_id)}</h1>
    <p class="run-meta">{html.escape(trace.get('timestamp', ''))} · source: {html.escape(trace.get('source', ''))}</p>

    <div class="phone">
      <div class="label">USSD SEQUENCE</div>
      <div class="readout">{html.escape(ussd_sequence) or '—'}</div>
      {dial_html}
    </div>

    {stage_html}
    """
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


class TraceHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            content = render_index()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif path == "/manifest.json":
            manifest_path = Path(__file__).parent / "static" / "manifest.json"
            if manifest_path.exists():
                content = manifest_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/manifest+json")
            else:
                content = b"Not found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
        elif path.startswith("/static/"):
            static_path = Path(__file__).parent / path.lstrip("/")
            if static_path.exists() and static_path.is_file():
                content = static_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
            else:
                content = b"Not found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
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

    def do_POST(self):  # noqa: N802
        path = self.path.split("?")[0]

        if path == "/run-audio":
            self._run_audio()
            return

        if path == "/run-record":
            self._run_record()
            return

        if path != "/run":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")
        fields = parse_qs(raw_body)
        text = (fields.get("text", [""])[0]).strip()

        if not text:
            content = render_index(error="Type a command first.")
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        try:
            from src.pipeline import run_pipeline
            result = run_pipeline(model_name="logistic_regression", raw_text_override=text, source="text")
            run_id = result["run_id"]
        except Exception as exc:  # surface pipeline errors instead of a bare 500
            print("=" * 60)
            print("PIPELINE ERROR (text run):")
            traceback.print_exc()
            print("=" * 60)
            content = render_index(error=f"Pipeline error: {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(303)
        self.send_header("Location", f"/trace/{run_id}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _run_audio(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        fields = parse_multipart(body, content_type)
        audio_field = fields.get("audio")

        if not audio_field or not audio_field["content"]:
            content = render_index(error="Choose or record an audio clip first.")
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        # Preserve the real extension when the browser (file picker or
        # MediaRecorder) sends one, since browser mic recordings are usually
        # webm/ogg, not wav. Whisper/ffmpeg mostly sniff content over
        # extension, but keeping it accurate avoids confusion either way.
        filename = audio_field.get("filename") or ""
        suffix = Path(filename).suffix if filename else ""
        if not suffix or len(suffix) > 6:
            suffix = ".webm"
        saved_path = UPLOADS_DIR / f"upload-{uuid.uuid4().hex[:8]}{suffix}"
        saved_path.write_bytes(audio_field["content"])

        try:
            from src.pipeline import run_pipeline
            result = run_pipeline(audio_path=str(saved_path), source="upload")
            run_id = result["run_id"]
        except Exception as exc:
            print("=" * 60)
            print("PIPELINE ERROR (audio run):")
            traceback.print_exc()
            print("=" * 60)
            content = render_index(error=f"Pipeline error: {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(303)
        self.send_header("Location", f"/trace/{run_id}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _run_record(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")
        fields = parse_qs(raw_body)
        try:
            duration = int(fields.get("duration", ["5"])[0])
        except ValueError:
            duration = 5

        try:
            from src.pipeline import run_pipeline
            # No audio_path, no raw_text_override -> same mic-recording path
            # as `python main.py --record`.
            result = run_pipeline(record_duration=duration)
            run_id = result["run_id"]
        except Exception as exc:
            print("=" * 60)
            print("PIPELINE ERROR (server-mic run):")
            traceback.print_exc()
            print("=" * 60)
            content = render_index(error=f"Recording/pipeline error: {exc}")
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(303)
        self.send_header("Location", f"/trace/{run_id}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[server] {self.address_string()} {fmt % args}")


def serve(port=8000, host="127.0.0.1"):
    server = ThreadingHTTPServer((host, port), TraceHandler)
    print(f"Sema, Tuma running at http://{host}:{port}")
    print("   Type a command on the home page, or open a past run to see its trace.")
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
