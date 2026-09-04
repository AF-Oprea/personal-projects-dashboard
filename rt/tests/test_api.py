import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from rt.radio import MetaCache, StationStore
from rt.server import make_server


class ApiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = StationStore(Path(tmp.name) / "station.json")
        meta = MetaCache(
            fetch=lambda video_id: {
                "id": video_id,
                "title": "Night Drive",
                "author": "Local FM",
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                "error": None,
            }
        )
        self.server = make_server("127.0.0.1", 0, store=store, meta=meta)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        def _stop():
            self.server.shutdown()
            self.server.server_close()

        self.addCleanup(_stop)
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def _json(self, path, payload=None, method="GET"):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_and_home(self):
        status, body = self._json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        request = Request(self.base + "/")
        with urlopen(request, timeout=5) as response:
            html = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("R&amp;T", html)
            self.assertIn("YouTube playlist", html)

    def test_tune_and_control(self):
        status, body = self._json(
            "/api/tune",
            {"url": "https://www.youtube.com/playlist?list=PLabcdefghijklmnopqrstuvwx01234567"},
            method="POST",
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["tuned"])
        self.assertEqual(body["station"]["playlist_id"], "PLabcdefghijklmnopqrstuvwx01234567")

        status, body = self._json("/api/station")
        self.assertTrue(body["tuned"])

        status, body = self._json("/api/control", {"shuffle": True, "loop": True}, method="POST")
        self.assertTrue(body["station"]["shuffle"])

        status, body = self._json("/api/meta", {"ids": ["dQw4w9wgGcQ"]}, method="POST")
        self.assertEqual(body["tracks"][0]["title"], "Night Drive")

    def test_rejects_bad_playlist_and_path_escape(self):
        request = Request(
            self.base + "/api/tune",
            data=json.dumps({"url": "https://example.com/playlist?list=PLaaaaaaaa"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as ctx:
            urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

        with self.assertRaises(HTTPError) as ctx:
            urlopen(self.base + "/../radio.py", timeout=5)
        self.assertIn(ctx.exception.code, {403, 404})


if __name__ == "__main__":
    unittest.main()
