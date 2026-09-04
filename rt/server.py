"""Stdlib HTTP server for the R&T local radio."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .radio import (
    MetaCache,
    RadioError,
    StationStore,
    new_station,
    parse_playlist_id,
    public_station,
)

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
STATION_PATH = DATA_DIR / "station.json"
MAX_BODY = 64 * 1024
MAX_META_IDS = 24


class RadioHTTPServer(ThreadingHTTPServer):
    def __init__(self, addr: tuple[str, int], store: StationStore, meta: MetaCache):
        super().__init__(addr, RadioHandler)
        self.store = store
        self.meta = meta


class RadioHandler(BaseHTTPRequestHandler):
    server_version = f"RTRadio/{__version__}"

    @property
    def radio_server(self) -> RadioHTTPServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/health":
            self._json(
                {
                    "ok": True,
                    "version": __version__,
                    "name": "R&T",
                }
            )
            return
        if path == "/api/station":
            self._json(public_station(self.radio_server.store.get()))
            return
        self._static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            body = self._read_json()
        except RadioError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        try:
            if path == "/api/tune":
                self._json(self._tune(body), status=HTTPStatus.OK)
                return
            if path == "/api/control":
                self._json(self._control(body))
                return
            if path == "/api/meta":
                self._json({"tracks": self._meta(body)})
                return
        except RadioError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except FileNotFoundError:
            self._error(HTTPStatus.NOT_FOUND, "Not found.")
            return

        self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint.")

    def _tune(self, body: dict[str, Any]) -> dict[str, Any]:
        url = str(body.get("url") or "")
        playlist_id = parse_playlist_id(url)
        current = self.radio_server.store.get() or {}
        station = new_station(playlist_id, url)
        if current.get("playlist_id") == playlist_id:
            station["shuffle"] = bool(current.get("shuffle"))
            station["loop"] = bool(current.get("loop", True))
        self.radio_server.store.save(station)
        return public_station(station)

    def _control(self, body: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if "shuffle" in body:
            fields["shuffle"] = bool(body["shuffle"])
        if "loop" in body:
            fields["loop"] = bool(body["loop"])
        if not fields:
            raise RadioError("No station controls to update.")
        station = self.radio_server.store.update(**fields)
        return public_station(station)

    def _meta(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        ids = body.get("ids")
        if not isinstance(ids, list) or not ids:
            raise RadioError("Send a list of video ids.")
        if len(ids) > MAX_META_IDS:
            raise RadioError(f"Ask for at most {MAX_META_IDS} tracks at a time.")
        clean = [str(item) for item in ids]
        return self.radio_server.meta.get_many(clean)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise RadioError("Request too large.")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RadioError("JSON body required.") from exc
        if not isinstance(payload, dict):
            raise RadioError("JSON object required.")
        return payload

    def _static(self, path: str) -> None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (WEB_DIR / relative).resolve()
        web_root = WEB_DIR.resolve()
        if web_root not in candidate.parents and candidate != web_root:
            self._error(HTTPStatus.FORBIDDEN, "Forbidden.")
            return
        if not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "Not found.")
            return
        mime = {
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
            ".html": "text/html; charset=utf-8",
        }.get(candidate.suffix)
        if not mime:
            mime, _ = mimetypes.guess_type(str(candidate))
        data = candidate.read_bytes()
        self._bytes(data, mime or "application/octet-stream")

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self._bytes(data, "application/json; charset=utf-8", status)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json({"ok": False, "error": message}, status=status)

    def _bytes(self, data: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


def make_server(
    host: str,
    port: int,
    store: StationStore | None = None,
    meta: MetaCache | None = None,
) -> RadioHTTPServer:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    station_store = store or StationStore(STATION_PATH)
    return RadioHTTPServer((host, port), station_store, meta or MetaCache())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rt",
        description="R&T — play a YouTube playlist like a local radio station.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (use 0.0.0.0 for LAN).")
    parser.add_argument("--port", type=int, default=8787, help="Port (default 8787).")
    parser.add_argument(
        "--playlist",
        default="",
        help="Optional YouTube playlist URL or id to pre-tune.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = make_server(args.host, args.port)
    if args.playlist:
        playlist_id = parse_playlist_id(args.playlist)
        server.store.save(new_station(playlist_id, args.playlist))
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    print(f"R&T v{__version__} on http://{display_host}:{args.port}", flush=True)
    print("Paste a YouTube playlist link and Tune In.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nR&T off air.", flush=True)
    finally:
        server.server_close()
    return 0
