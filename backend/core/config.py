"""Configuration centrale — chargée depuis les variables d'environnement (.env)."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Clé API Claude — voir https://console.anthropic.com
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Modèle utilisé pour la génération de contenu.
    # Opus 4.8 = qualité maximale. Passer à claude-sonnet-4-6 pour réduire les coûts.
    MODEL: str = os.getenv("REFLOW_MODEL", "claude-opus-4-8")

    # Langues de sous-titres à essayer en priorité (dans l'ordre).
    SUBTITLE_LANGS: list[str] = os.getenv("REFLOW_SUBTITLE_LANGS", "en,fr").split(",")

    # Quota gratuit : nombre de vidéos/mois avant paywall (voir core/quota.py).
    FREE_MONTHLY_QUOTA: int = int(os.getenv("REFLOW_FREE_QUOTA", "3"))

    # Origines autorisées pour le CORS (frontend).
    CORS_ORIGINS: list[str] = os.getenv(
        "REFLOW_CORS_ORIGINS", "http://localhost:4321,http://localhost:3000"
    ).split(",")

    # Active la transcription locale par Whisper en secours quand aucun
    # sous-titre n'est disponible (nécessite faster-whisper installé).
    ENABLE_WHISPER_FALLBACK: bool = os.getenv("REFLOW_WHISPER", "false").lower() == "true"


settings = Settings()
