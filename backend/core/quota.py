"""Gestion du quota — stub MVP.

⚠️ Version fichier-JSON en mémoire, suffisante pour tester le paywall en local.
En production, remplacer par une table Supabase (`usage`) indexée sur user_id,
et compter les traitements réussis. Voir README → "Passer en production".
"""
import json
import time
from pathlib import Path

from .config import settings

_STORE = Path(__file__).parent.parent / ".quota_store.json"


def _load() -> dict:
    if _STORE.exists():
        return json.loads(_STORE.read_text())
    return {}


def _save(data: dict) -> None:
    _STORE.write_text(json.dumps(data))


def _current_period() -> str:
    """Clé de période mensuelle, ex. '2026-07'."""
    return time.strftime("%Y-%m")


def peek(identifier: str) -> int:
    """Nombre d'unités restantes pour `identifier` ce mois, sans rien réserver."""
    data = _load()
    user = data.get(identifier, {})
    if user.get("period") != _current_period():
        return settings.FREE_MONTHLY_QUOTA
    return max(0, settings.FREE_MONTHLY_QUOTA - user.get("count", 0))


def check_and_reserve(identifier: str) -> tuple[bool, int]:
    """Vérifie le quota pour `identifier` (IP ou user_id) et réserve une unité.

    Retourne (autorisé, unités_restantes). N'incrémente que si autorisé.
    """
    data = _load()
    period = _current_period()
    user = data.get(identifier, {})

    # Réinitialise le compteur au changement de mois.
    if user.get("period") != period:
        user = {"period": period, "count": 0}

    used = user["count"]
    if used >= settings.FREE_MONTHLY_QUOTA:
        return False, 0

    user["count"] = used + 1
    data[identifier] = user
    _save(data)
    return True, settings.FREE_MONTHLY_QUOTA - user["count"]
