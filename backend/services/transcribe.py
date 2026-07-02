"""Récupération du transcript d'une vidéo/podcast.

Stratégie (du moins cher au plus cher) :
  1. Sous-titres YouTube (manuels ou auto-générés) via yt-dlp — gratuit, instantané.
  2. Fallback Whisper local sur l'audio téléchargé — plus lent, nécessite un GPU
     idéalement (activer via REFLOW_WHISPER=true).
"""
from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass

import yt_dlp

from core.config import settings


@dataclass
class Transcript:
    title: str
    duration: int  # secondes
    text: str
    source: str  # "subtitles" | "whisper"


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_transcript(url: str) -> Transcript:
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Sans titre")
    duration = int(info.get("duration") or 0)

    # 1) Cherche des sous-titres dans les langues préférées.
    for source_field in ("subtitles", "automatic_captions"):
        tracks = info.get(source_field) or {}
        for lang in settings.SUBTITLE_LANGS:
            # Gère les variantes ("en", "en-US", "en-orig", …).
            match = next(
                (k for k in tracks if k == lang or k.startswith(f"{lang}-")), None
            )
            if not match:
                continue
            text = _download_caption_track(tracks[match])
            if text:
                return Transcript(title, duration, _clean(text), "subtitles")

    # 2) Fallback Whisper.
    if settings.ENABLE_WHISPER_FALLBACK:
        text = _whisper_transcribe(url)
        return Transcript(title, duration, _clean(text), "whisper")

    raise RuntimeError(
        "Aucun sous-titre disponible pour cette vidéo. "
        "Active la transcription Whisper (REFLOW_WHISPER=true) pour ce cas."
    )


def _download_caption_track(formats: list[dict]) -> str | None:
    """Télécharge une piste de sous-titres et en extrait le texte brut."""
    # Préfère json3 (structuré, facile à parser), sinon vtt.
    fmt = next((f for f in formats if f.get("ext") == "json3"), None)
    if fmt:
        raw = _http_get(fmt["url"])
        return _parse_json3(raw)

    fmt = next((f for f in formats if f.get("ext") == "vtt"), None)
    if fmt:
        raw = _http_get(fmt["url"])
        return _parse_vtt(raw)

    return None


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_json3(raw: str) -> str:
    data = json.loads(raw)
    parts: list[str] = []
    for event in data.get("events", []):
        for seg in event.get("segs", []) or []:
            if seg.get("utf8"):
                parts.append(seg["utf8"])
    return "".join(parts)


def _parse_vtt(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if line.isdigit():
            continue
        lines.append(re.sub(r"<[^>]+>", "", line))  # retire les balises inline
    return " ".join(lines)


def _whisper_transcribe(url: str) -> str:
    """Télécharge l'audio et le transcrit localement avec faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "faster-whisper n'est pas installé. `pip install faster-whisper`"
        ) from e

    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/audio.%(ext)s"
        opts = {
            "format": "bestaudio/best",
            "outtmpl": out,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
            ],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        audio_path = f"{tmp}/audio.mp3"
        model = WhisperModel("base", device="auto", compute_type="int8")
        segments, _ = model.transcribe(audio_path)
        return " ".join(seg.text for seg in segments)
