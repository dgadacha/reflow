"""Cache de développement.

Quand REFLOW_DEV_MODE=true, le résultat complet de /api/process est mis en cache
sur disque, indexé par (url + persona + voix). Les tests répétés avec la même vidéo
ne rappellent donc ni la transcription ni l'API Claude. Sans effet en production.
"""
import hashlib
import json
from pathlib import Path

from .config import settings

_DIR = Path(__file__).parent.parent / ".cache"


def _key(url: str, persona: str | None, voice: str | None) -> str:
    raw = f"{url}|{persona or ''}|{voice or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get(url: str, persona: str | None, voice: str | None) -> dict | None:
    if not settings.DEV_MODE:
        return None
    f = _DIR / f"{_key(url, persona, voice)}.json"
    if f.exists():
        return json.loads(f.read_text())
    return None


def put(url: str, persona: str | None, voice: str | None, data: dict) -> None:
    if not settings.DEV_MODE:
        return
    _DIR.mkdir(exist_ok=True)
    f = _DIR / f"{_key(url, persona, voice)}.json"
    f.write_text(json.dumps(data))
