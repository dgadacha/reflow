"""Génération de contenu multi-formats à partir d'un transcript, via Claude.

Un seul appel API produit tous les formats en JSON structuré (structured outputs),
ce qui garantit un résultat directement exploitable côté frontend et minimise le coût.
"""
from __future__ import annotations

import json

from anthropic import Anthropic

from core.config import settings

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Schéma de sortie imposé au modèle (structured outputs).
# Contraintes : additionalProperties=false + required sur chaque objet.
_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "Résumé en 2-3 phrases de la vidéo.",
        },
        "seo_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5 propositions de titres d'article optimisés SEO.",
        },
        "blog_article": {
            "type": "string",
            "description": "Article de blog complet en Markdown (600-900 mots), "
            "avec titres de section, prêt à publier.",
        },
        "linkedin_post": {
            "type": "string",
            "description": "Post LinkedIn engageant avec hook, corps et CTA.",
        },
        "x_thread": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Thread X/Twitter : 5-8 tweets numérotés, <280 caractères chacun.",
        },
        "newsletter": {
            "type": "string",
            "description": "Section de newsletter avec objet accrocheur puis corps.",
        },
        "instagram_captions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 légendes Instagram/TikTok avec hashtags pertinents.",
        },
        "key_moments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "why": {
                        "type": "string",
                        "description": "Pourquoi ce moment ferait un bon clip court.",
                    },
                },
                "required": ["title", "why"],
            },
            "description": "3-5 moments forts à découper en clips courts.",
        },
    },
    "required": [
        "summary",
        "seo_titles",
        "blog_article",
        "linkedin_post",
        "x_thread",
        "newsletter",
        "instagram_captions",
        "key_moments",
    ],
}

_SYSTEM = (
    "Tu es un moteur de repurposing de contenu pour créateurs et équipes marketing. "
    "À partir de la transcription d'une vidéo ou d'un podcast, tu produis un ensemble "
    "de formats prêts à publier, fidèles au fond et au ton de la source. "
    "Tu écris dans la langue de la transcription. Style clair, concret, sans remplissage."
)

# Longueur max de transcript envoyée au modèle (garde-fou coût/contexte).
_MAX_TRANSCRIPT_CHARS = 40_000


def generate_content(title: str, transcript: str) -> dict:
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:_MAX_TRANSCRIPT_CHARS] + "\n[...transcription tronquée...]"

    prompt = (
        f"Titre de la source : {title}\n\n"
        f"Transcription :\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        "Génère tous les formats demandés à partir de ce contenu."
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
