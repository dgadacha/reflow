"""Reflow — API FastAPI.

Endpoint principal : POST /api/process { url } → tous les formats de contenu.
Lancement en local : uvicorn main:app --reload --port 8787
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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


@app.post("/api/process")
def process(req: ProcessRequest, request: Request) -> dict:
    # --- Cache dev : ressert le résultat sans rappeler Claude ------------------
    cached = cache.get(req.url, req.persona, req.voice)
    if cached is not None:
        return {**cached, "from_cache": True}

    if not settings.ANTHROPIC_API_KEY:
        return _error("Clé ANTHROPIC_API_KEY manquante côté serveur.", 500)

    # --- Paywall / quota ------------------------------------------------------
    # MVP : quota par IP. En production, remplacer par l'user_id issu de l'auth
    # Supabase et vérifier l'abonnement Stripe actif avant d'appeler check_and_reserve.
    # En mode dev, le quota est ignoré.
    if settings.DEV_MODE:
        remaining = settings.FREE_MONTHLY_QUOTA
    else:
        identifier = request.client.host if request.client else "anonymous"
        allowed, remaining = check_and_reserve(identifier)
        if not allowed:
            return _error(
                "Quota gratuit épuisé pour ce mois. Passe à un plan payant pour continuer.",
                402,
            )

    # --- Traitement -----------------------------------------------------------
    try:
        transcript = get_transcript(req.url)
    except Exception as e:  # noqa: BLE001 — surface l'erreur au client
        return _error(f"Transcription impossible : {e}", 422)

    try:
        formats = generate_content(
            transcript.title, transcript.text, req.persona, req.voice
        )
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


def _error(message: str, code: int) -> dict:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=code, content={"error": message})
