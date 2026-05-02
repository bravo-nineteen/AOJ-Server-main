"""TTS API route — /api/tts/speak

POST /api/tts/speak   { "text": "..." }  → audio/wav stream
GET  /api/tts/status                     → { "available": bool, "voice": str }
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field

from app.services.tts_service import generate_speech_wav, tts_engine_status

router = APIRouter(prefix="/api/tts", tags=["TTS"])


class TTSSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.get("/status")
def tts_status() -> JSONResponse:
    """Report whether offline TTS is available and which engine/voice is active."""
    return JSONResponse(tts_engine_status())


@router.post("/speak")
def tts_speak(payload: TTSSpeakRequest) -> Response:
    """Generate offline speech and return WAV audio bytes."""
    wav = generate_speech_wav(payload.text)
    if wav is None:
        return Response(status_code=503, content=b"", media_type="audio/wav")
    return Response(content=wav, media_type="audio/wav")
