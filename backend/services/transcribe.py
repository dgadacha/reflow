"""Récupération du transcript d'une vidéo/podcast, avec timecodes conservés.

Stratégie (du moins cher au plus cher) :
  1. Sous-titres YouTube (manuels ou auto) via yt-dlp — gratuit, instantané.
  2. Fallback Whisper local sur l'audio (REFLOW_WHISPER=true).

On conserve les timecodes de chaque segment pour produire une transcription
horodatée `[MM:SS]` que Claude peut citer (timecodes réels des clips).
"""
from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass, field

import yt_dlp

from core.config import settings


@dataclass
class Transcript:
    title: str
    duration: int  # secondes
    text: str  # texte propre (affichage)
    timed: str  # texte horodaté [MM:SS] (pour le modèle)
    source: str  # "subtitles" | "whisper"
    segments: list = field(default_factory=list)  # [{start: float, text: str}]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _build_timed(segments: list[dict], every: int = 15) -> str:
    """Insère un marqueur [MM:SS] toutes les ~`every` secondes."""
    out: list[str] = []
    next_mark = 0.0
    for seg in segments:
        start = seg.get("start", 0.0)
        if start >= next_mark:
            out.append(f"\n[{_fmt_ts(start)}] ")
            next_mark = start + every
        out.append(seg["text"])
    return "".join(out).strip()


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

    for source_field in ("subtitles", "automatic_captions"):
        tracks = info.get(source_field) or {}
        for lang in settings.SUBTITLE_LANGS:
            match = next((k for k in tracks if k == lang or k.startswith(f"{lang}-")), None)
            if not match:
                continue
            segments = _download_caption_track(tracks[match])
            if segments:
                return _build(title, duration, segments, "subtitles")

    if settings.ENABLE_WHISPER_FALLBACK:
        segments = _whisper_transcribe(url)
        return _build(title, duration, segments, "whisper")

    raise RuntimeError(
        "Aucun sous-titre disponible pour cette vidéo. "
        "Active la transcription Whisper (REFLOW_WHISPER=true) pour ce cas."
    )


def _build(title: str, duration: int, segments: list[dict], source: str) -> Transcript:
    text = _clean(" ".join(s["text"] for s in segments))
    timed = _build_timed(segments)
    return Transcript(title, duration, text, timed, source, segments)


def _download_caption_track(formats: list[dict]) -> list[dict] | None:
    """Télécharge une piste de sous-titres → liste de segments {start, text}."""
    fmt = next((f for f in formats if f.get("ext") == "json3"), None)
    if fmt:
        return _parse_json3(_http_get(fmt["url"]))
    fmt = next((f for f in formats if f.get("ext") == "vtt"), None)
    if fmt:
        return _parse_vtt(_http_get(fmt["url"]))
    return None


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _parse_json3(raw: str) -> list[dict]:
    data = json.loads(raw)
    segments: list[dict] = []
    for event in data.get("events", []):
        text = "".join(s.get("utf8", "") for s in event.get("segs", []) or [])
        text = text.strip()
        if text:
            segments.append({"start": (event.get("tStartMs", 0)) / 1000.0, "text": text})
    return segments


def _vtt_ts_to_sec(ts: str) -> float:
    # "HH:MM:SS.mmm" ou "MM:SS.mmm"
    parts = ts.split(":")
    parts = [float(p.replace(",", ".")) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def _parse_vtt(raw: str) -> list[dict]:
    segments: list[dict] = []
    cur_start = None
    buf: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if "-->" in line:
            if cur_start is not None and buf:
                segments.append({"start": cur_start, "text": " ".join(buf)})
            cur_start = _vtt_ts_to_sec(line.split("-->")[0].strip().split(" ")[0])
            buf = []
        elif not line or line.startswith(("WEBVTT", "Kind:", "Language:")) or line.isdigit():
            continue
        else:
            buf.append(re.sub(r"<[^>]+>", "", line))
    if cur_start is not None and buf:
        segments.append({"start": cur_start, "text": " ".join(buf)})
    return segments


def _whisper_transcribe(url: str) -> list[dict]:
    """Télécharge l'audio et le transcrit localement avec faster-whisper."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("faster-whisper n'est pas installé. `pip install faster-whisper`") from e

    with tempfile.TemporaryDirectory() as tmp:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{tmp}/audio.%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        model = WhisperModel("base", device="auto", compute_type="int8")
        segments, _ = model.transcribe(f"{tmp}/audio.mp3")
        return [{"start": seg.start, "text": seg.text.strip()} for seg in segments]
