"""Génération de contenu multi-formats à partir d'un transcript, via Claude.

Périmètre V1 (simplifié) : calendrier éditorial + posts (LinkedIn/Facebook/Instagram)
+ carrousel unifié + thread + clips. Newsletter / article / SEO sont reportés en V2.
Un seul appel API produit tout en JSON structuré (coût minimal).
"""
from __future__ import annotations

import json

from anthropic import Anthropic

from core.config import settings

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Schéma de sortie imposé au modèle (structured outputs).
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "Résumé en 2-3 phrases de la vidéo.",
        },
        "weekly_calendar": {
            "type": "array",
            "description": "Calendrier éditorial Lundi→Vendredi répartissant les contenus.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "day": {"type": "string", "description": "Jour (ex. Lundi)."},
                    "channel": {"type": "string", "description": "Canal (LinkedIn, X, Instagram…)."},
                    "action": {"type": "string", "description": "Ce qu'il faut publier ce jour-là."},
                },
                "required": ["day", "channel", "action"],
            },
        },
        "posts": {
            "type": "array",
            "description": "Un post court prêt à publier par plateforme : LinkedIn, Facebook, Instagram.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "platform": {"type": "string", "description": "LinkedIn, Facebook ou Instagram."},
                    "content": {"type": "string", "description": "Le post complet, adapté à la plateforme."},
                },
                "required": ["platform", "content"],
            },
        },
        "carousel": {
            "type": "object",
            "additionalProperties": False,
            "description": "Carrousel unifié (LinkedIn / Instagram / TikTok).",
            "properties": {
                "title": {"type": "string", "description": "Slide de couverture."},
                "slides": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Contenu de chaque slide (6-8 slides).",
                },
                "cta": {"type": "string", "description": "Call-to-action final."},
            },
            "required": ["title", "slides", "cta"],
        },
        "thread": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Thread X/Twitter (utilisable aussi sur Threads) : 5-8 posts numérotés.",
        },
        "clips": {
            "type": "array",
            "description": "3-5 moments forts à découper en clips courts (Reels/Shorts/TikTok).",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "timestamp": {"type": "string", "description": "Timecode du moment, repris EXACTEMENT d'un marqueur [MM:SS] proche dans la transcription (ex. '12:05')."},
                    "title": {"type": "string", "description": "Titre du moment fort."},
                    "hook": {"type": "string", "description": "Phrase d'accroche pour le short."},
                    "why": {"type": "string", "description": "Pourquoi ce moment fonctionne en clip."},
                    "score": {"type": "integer", "description": "Potentiel viral estimé de 0 à 100 (accroche, émotion, clarté, partageabilité)."},
                },
                "required": ["timestamp", "title", "hook", "why", "score"],
            },
        },
    },
    "required": ["summary", "weekly_calendar", "posts", "carousel", "thread", "clips"],
}

_SYSTEM = (
    "Tu es un stratège de contenu pour créateurs et équipes marketing. "
    "À partir de la transcription d'une vidéo, tu produis un plan de la semaine : "
    "un calendrier Lundi→Vendredi, un post court adapté par plateforme (LinkedIn, "
    "Facebook, Instagram), un carrousel, un thread, et des idées de clips avec accroche. "
    "La transcription contient des marqueurs de temps [MM:SS] : pour chaque clip, "
    "reprends le timecode du marqueur le plus proche du moment cité (n'invente jamais). "
    "Tout est fidèle au fond et au ton de la source. "
    "Tu écris dans la langue de la transcription. Style clair, concret, sans remplissage."
)

_MAX_TRANSCRIPT_CHARS = 40_000


def generate_content(
    title: str,
    transcript: str,
    persona: str | None = None,
    voice: str | None = None,
) -> dict:
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:_MAX_TRANSCRIPT_CHARS] + "\n[...transcription tronquée...]"

    context_lines = []
    if persona and persona.lower() != "auto":
        context_lines.append(f"Audience / profil cible : {persona}.")
    if voice and voice.lower() != "auto":
        context_lines.append(f"Voix de marque à respecter partout : {voice}.")
    context = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    prompt = (
        f"{context}"
        f"Titre de la source : {title}\n\n"
        f"Transcription horodatée (marqueurs [MM:SS]) :\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        "Génère le plan de la semaine et tous les contenus demandés."
    )

    response = _client.messages.create(
        model=settings.MODEL,
        max_tokens=16000,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Le modèle a refusé de traiter ce contenu.")

    text = "".join(b.text for b in response.content if b.type == "text")
    return json.loads(text)
