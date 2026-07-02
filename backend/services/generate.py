"""Génération de contenu multi-formats à partir d'un transcript, via Claude.

Un seul appel API produit un plan éditorial complet en JSON structuré :
un calendrier de la semaine + tous les formats (posts, carrousels, thread, etc.),
adaptés à un persona et à une voix de marque. Un appel = coût minimal.
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
        "weekly_calendar": {
            "type": "array",
            "description": "Calendrier éditorial de la semaine (Lundi→Vendredi). "
            "Répartit intelligemment les formats ci-dessous sur 5 jours.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "day": {"type": "string", "description": "Jour (ex. Lundi)."},
                    "channel": {
                        "type": "string",
                        "description": "Canal (LinkedIn, X, Newsletter, Blog, Reels…).",
                    },
                    "action": {
                        "type": "string",
                        "description": "Ce qu'il faut publier ce jour-là, en une phrase.",
                    },
                },
                "required": ["day", "channel", "action"],
            },
        },
        "linkedin_post": {
            "type": "string",
            "description": "Post LinkedIn engageant avec hook, corps et CTA.",
        },
        "linkedin_carousel": {
            "type": "object",
            "additionalProperties": False,
            "description": "Carrousel LinkedIn slide par slide.",
            "properties": {
                "title": {"type": "string", "description": "Titre / slide de couverture."},
                "slides": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Contenu de chaque slide (6-10 slides).",
                },
                "cta": {"type": "string", "description": "Call-to-action final."},
            },
            "required": ["title", "slides", "cta"],
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
        "instagram_carousel": {
            "type": "object",
            "additionalProperties": False,
            "description": "Carrousel Instagram slide par slide.",
            "properties": {
                "cover": {"type": "string", "description": "Texte de la slide de couverture."},
                "slides": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Contenu de chaque slide (5-8 slides).",
                },
                "caption": {"type": "string", "description": "Légende + hashtags du post."},
            },
            "required": ["cover", "slides", "caption"],
        },
        "blog_article": {
            "type": "string",
            "description": "Article de blog complet en Markdown (600-900 mots), "
            "avec titres de section, prêt à publier.",
        },
        "seo_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "5 propositions de titres d'article optimisés SEO.",
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
        "weekly_calendar",
        "linkedin_post",
        "linkedin_carousel",
        "x_thread",
        "newsletter",
        "instagram_carousel",
        "blog_article",
        "seo_titles",
        "key_moments",
    ],
}

_SYSTEM = (
    "Tu es un stratège de contenu pour créateurs et équipes marketing. "
    "À partir de la transcription d'une vidéo ou d'un podcast, tu produis un plan "
    "éditorial complet pour une semaine : un calendrier Lundi→Vendredi qui répartit "
    "les formats, plus chaque format prêt à publier (posts, carrousels, thread, "
    "newsletter, article). Tout est fidèle au fond et au ton de la source. "
    "Tu écris dans la langue de la transcription. Style clair, concret, sans remplissage."
)

# Longueur max de transcript envoyée au modèle (garde-fou coût/contexte).
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
        f"Transcription :\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        "Génère le plan éditorial de la semaine et tous les formats demandés."
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
