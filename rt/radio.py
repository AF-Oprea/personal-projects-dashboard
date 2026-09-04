"""Playlist URL parsing, station state, and YouTube metadata helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

# YouTube list IDs: uploads (UU), playlist (PL), mixes (RD/OL), etc.
PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,80}$")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
USER_AGENT = "R-and-T-radio/0.1 (local; +https://github.com/AF-Oprea/personal-projects-dashboard)"


class RadioError(ValueError):
    """Invalid station input."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _host(netloc: str) -> str:
    host = netloc.lower().split("@")[-1]
    if host.startswith("[") and "]" in host:
        host = host[1 : host.index("]")]
    elif ":" in host:
        host = host.rsplit(":", 1)[0]
    if host.startswith("www."):
        return host
    return host


def parse_playlist_id(raw: str) -> str:
    """Extract a YouTube playlist/list id from a URL or a bare id."""
    if raw is None:
        raise RadioError("Paste a YouTube playlist link.")
    text = raw.strip()
    if not text:
        raise RadioError("Paste a YouTube playlist link.")
    if any(ch.isspace() for ch in text) and "http" not in text.lower():
        raise RadioError("That does not look like a YouTube playlist link.")

    if PLAYLIST_ID_RE.match(text) and "://" not in text:
        return text

    candidate = text
    if "://" not in candidate:
        candidate = "https://" + candidate.lstrip("/")

    parsed = urlparse(candidate)
    host = _host(parsed.netloc)
    if host not in YOUTUBE_HOSTS:
        raise RadioError("Only YouTube playlist links are accepted.")

    query = parse_qs(parsed.query)
    list_ids = query.get("list") or []
    if list_ids:
        playlist_id = list_ids[0].strip()
        if PLAYLIST_ID_RE.match(playlist_id):
            return playlist_id
        raise RadioError("The playlist id in that link is invalid.")

    raise RadioError("That YouTube link has no playlist id (missing list=).")


def playlist_watch_url(playlist_id: str) -> str:
    return f"https://www.youtube.com/playlist?list={playlist_id}"


def playlist_embed_url(playlist_id: str) -> str:
    """Official playlist embed — never /embed/? without an id."""
    query = urlencode(
        {
            "list": playlist_id,
            "autoplay": "1",
            "loop": "1",
            "rel": "0",
            "modestbranding": "1",
            "playsinline": "1",
            "enablejsapi": "1",
            "controls": "1",
        }
    )
    return f"https://www.youtube.com/embed/videoseries?{query}"


def video_watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def validate_video_id(video_id: str) -> str:
    if not VIDEO_ID_RE.match(video_id or ""):
        raise RadioError("Invalid video id.")
    return video_id


def fm_frequency(playlist_id: str) -> str:
    """Stable decorative FM readout derived from the playlist id."""
    total = sum(ord(ch) for ch in playlist_id)
    mhz = 87.5 + (total % 205) / 10.0
    return f"{mhz:.1f}"


def new_station(playlist_id: str, source_url: str) -> dict[str, Any]:
    return {
        "playlist_id": playlist_id,
        "source_url": source_url.strip(),
        "watch_url": playlist_watch_url(playlist_id),
        "frequency": fm_frequency(playlist_id),
        "tuned_at": utc_now_iso(),
        "title": None,
        "tracks": [],
        "shuffle": False,
        "loop": True,
    }


class StationStore:
    def __init__(self, path: Path):
        self.path = path
        self._station: dict[str, Any] | None = None
        self.load()

    def load(self) -> dict[str, Any] | None:
        if self.path.exists():
            try:
                self._station = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._station = None
        return self._station

    def get(self) -> dict[str, Any] | None:
        return self._station

    def save(self, station: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._station = station
        self.path.write_text(json.dumps(station, indent=2) + "\n", encoding="utf-8")
        return station

    def update(self, **fields: Any) -> dict[str, Any]:
        current = dict(self._station or {})
        if not current.get("playlist_id"):
            raise RadioError("Tune a playlist first.")
        current.update(fields)
        return self.save(current)

    def clear(self) -> None:
        self._station = None
        if self.path.exists():
            self.path.unlink()


class MetaCache:
    def __init__(self, fetch: Callable[[str], dict[str, Any]] | None = None):
        self._cache: dict[str, dict[str, Any]] = {}
        self._fetch = fetch or fetch_oembed

    def get_many(self, video_ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw_id in video_ids:
            video_id = validate_video_id(raw_id)
            if video_id not in self._cache:
                try:
                    self._cache[video_id] = self._fetch(video_id)
                except RadioError as exc:
                    self._cache[video_id] = {
                        "id": video_id,
                        "title": None,
                        "author": None,
                        "thumbnail": thumbnail_url(video_id),
                        "error": str(exc),
                    }
            out.append(self._cache[video_id])
        return out


def fetch_oembed(video_id: str, opener: Callable[..., Any] = urlopen) -> dict[str, Any]:
    validate_video_id(video_id)
    oembed = (
        "https://www.youtube.com/oembed?format=json&url="
        + video_watch_url(video_id)
    )
    request = Request(oembed, headers={"User-Agent": USER_AGENT})
    try:
        with opener(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RadioError(f"YouTube metadata unavailable ({exc.code}).") from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise RadioError("Could not reach YouTube metadata.") from exc

    title = str(payload.get("title") or "").strip() or None
    author = str(payload.get("author_name") or "").strip() or None
    return {
        "id": video_id,
        "title": title,
        "author": author,
        "thumbnail": thumbnail_url(video_id),
        "error": None,
    }


def public_station(station: dict[str, Any] | None) -> dict[str, Any]:
    if not station:
        return {"tuned": False, "station": None}
    return {
        "tuned": True,
        "station": {
            "playlist_id": station["playlist_id"],
            "source_url": station.get("source_url"),
            "watch_url": station.get("watch_url"),
            "embed_url": playlist_embed_url(station["playlist_id"]),
            "frequency": station.get("frequency"),
            "tuned_at": station.get("tuned_at"),
            "shuffle": bool(station.get("shuffle")),
            "loop": bool(station.get("loop", True)),
        },
    }
