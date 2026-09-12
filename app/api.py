"""FastAPI service exposing the speech-to-USSD pipeline over HTTP."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
from pathlib import Path

from src.pipeline import run_pipeline
from src.trace import list_traces

app = FastAPI(title="Speech-to-USSD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptRequest(BaseModel):
    transcript: str
    model: str = "logistic_regression"


class PipelineResponse(BaseModel):
    run_id: str
    transcript: str
    normalized_text: str
    intent: str
    confidence: float
    slots: dict
    ussd_menu: str
    ussd: str


def _to_response(result: dict) -> PipelineResponse:
    return PipelineResponse(
        run_id=result["run_id"],
        transcript=result["whisper_transcript"],
        normalized_text=result["normalized_text"],
        intent=result["intent"],
        confidence=result["confidence"] or 0.0,
        slots=result.get("slots", {}),
        ussd_menu=result.get("ussd_menu", ""),
        ussd=result["ussd_sequence"],
    )


@app.post("/process", response_model=PipelineResponse)
def process_transcript(payload: TranscriptRequest):
    if not payload.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="transcript must not be empty",
        )

    result = run_pipeline(
        model_name=payload.model,
        raw_text_override=payload.transcript,
        source="text",
    )

    return _to_response(result)


@app.post("/process-audio", response_model=PipelineResponse)
async def process_audio(
    file: UploadFile = File(...),
    model: str = "logistic_regression",
):
    suffix = Path(file.filename).suffix or ".wav"

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    ) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = run_pipeline(
            audio_path=tmp_path,
            model_name=model,
            source="file",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return _to_response(result)


class TraceSummary(BaseModel):
    run_id: str
    timestamp: str
    intent: str | None = None
    transcript: str = ""


@app.get("/traces", response_model=list[TraceSummary])
def get_traces():
    traces = list_traces()

    return [
        TraceSummary(
            run_id=t["run_id"],
            timestamp=t["timestamp"],
            intent=t.get("intent"),
            transcript=t.get("whisper_transcript", ""),
        )
        for t in traces
    ]


@app.get("/health")
def health():
    return {"status": "ok"}