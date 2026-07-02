"""Reflow — API FastAPI.

- POST /api/process         → traitement complet, réponse JSON unique.
- POST /api/process/stream  → même traitement en SSE (progression étape par étape).
Lancement : uvicorn main:app --reload --port 8787
"""
from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from core import cache
from core.config import settings
from core.quota import check_and_reserve
from services.generate import generate_content
from services.transcribe import get_transcript

app = FastAPI(title="Reflow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    url: str
    persona: str | None = None
    voice: str | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.MODEL}


def _reserve_quota(request: Request) -> tuple[bool, int | None, str | None]:
    """(ok, remaining, error_message). Quota illimité en dev."""
    if settings.DEV_MODE:
        return True, None, None
    identifier = request.client.host if request.client else "anonymous"
    allowed, remaining = check_and_reserve(identifier)
    if not allowed:
        return False, None, "Quota gratuit épuisé pour ce mois. Passe à un plan payant pour continuer."
    return True, remaining, None


@app.post("/api/process")
def process(req: ProcessRequest, request: Request) -> dict:
    cached = cache.get(req.url, req.persona, req.voice)
    if cached is not None:
        return {**cached, "from_cache": True}
    if not settings.ANTHROPIC_API_KEY:
        return _error("Clé ANTHROPIC_API_KEY manquante côté serveur.", 500)

    ok, remaining, msg = _reserve_quota(request)
    if not ok:
        return _error(msg, 402)

    try:
        transcript = get_transcript(req.url)
    except Exception as e:  # noqa: BLE001
        return _error(f"Transcription impossible : {e}", 422)
    try:
        formats = generate_content(transcript.title, transcript.timed, req.persona, req.voice)
    except Exception as e:  # noqa: BLE001
        return _error(f"Génération impossible : {e}", 502)

    result = {
        "title": transcript.title,
        "duration": transcript.duration,
        "transcript_source": transcript.source,
        "transcript_chars": len(transcript.text),
        "transcript": transcript.text,
        "quota_remaining": remaining,
        "from_cache": False,
        "formats": formats,
    }
    cache.put(req.url, req.persona, req.voice, result)
    return result


@app.post("/api/process/stream")
def process_stream(req: ProcessRequest, request: Request) -> StreamingResponse:
    """Même traitement, émis en Server-Sent Events (progression réelle)."""

    def gen():
        cached = cache.get(req.url, req.persona, req.voice)
        if cached is not None:
            yield _sse("result", {**cached, "from_cache": True})
            yield _sse("done", {})
            return
        if not settings.ANTHROPIC_API_KEY:
            yield _sse("error", {"message": "Clé ANTHROPIC_API_KEY manquante côté serveur."})
            return

        ok, remaining, msg = _reserve_quota(request)
        if not ok:
            yield _sse("error", {"message": msg})
            return

        # Étape 1 — transcription
        yield _sse("step", {"name": "transcript", "state": "start"})
        try:
            transcript = get_transcript(req.url)
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"Transcription impossible : {e}"})
            return
        yield _sse("step", {"name": "transcript", "state": "done",
                            "detail": f"{len(transcript.text):,} caractères".replace(",", " ")})

        # Étape 2 — génération
        yield _sse("step", {"name": "generate", "state": "start"})
        try:
            formats = generate_content(transcript.title, transcript.timed, req.persona, req.voice)
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"Génération impossible : {e}"})
            return
        yield _sse("step", {"name": "generate", "state": "done"})

        result = {
            "title": transcript.title,
            "duration": transcript.duration,
            "transcript_source": transcript.source,
            "transcript_chars": len(transcript.text),
            "transcript": transcript.text,
            "quota_remaining": remaining,
            "from_cache": False,
            "formats": formats,
        }
        cache.put(req.url, req.persona, req.voice, result)
        yield _sse("result", result)
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _error(message: str, code: int):
    return JSONResponse(status_code=code, content={"error": message})
