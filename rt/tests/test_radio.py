import tempfile
import unittest
from pathlib import Path

from rt.radio import (
    MetaCache,
    RadioError,
    StationStore,
    fm_frequency,
    new_station,
    parse_playlist_id,
    public_station,
)


class ParsePlaylistTests(unittest.TestCase):
    def test_bare_id(self):
        self.assertEqual(parse_playlist_id("PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI"), "PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI")

    def test_playlist_url(self):
        url = "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMOVlXBW2UoqCZrJ8G"
        self.assertEqual(parse_playlist_id(url), "PLrAXtmRdnEQy6nuLMOVlXBW2UoqCZrJ8G")

    def test_watch_url_with_list(self):
        url = "https://www.youtube.com/watch?v=dQw4w9wgGcQ&list=PL4o29bINVT4EG_y-k5jGoOu3-Am8Nvi10"
        self.assertEqual(parse_playlist_id(url), "PL4o29bINVT4EG_y-k5jGoOu3-Am8Nvi10")

    def test_music_host(self):
        url = "https://music.youtube.com/playlist?list=OLAK5uy_k1Q2x0abcDEFGHijKLmnopqrsTUVwxyz12"
        self.assertEqual(parse_playlist_id(url), "OLAK5uy_k1Q2x0abcDEFGHijKLmnopqrsTUVwxyz12")

    def test_mobile_and_short_hosts(self):
        self.assertEqual(
            parse_playlist_id("https://m.youtube.com/playlist?list=PLabcdefghijkmnopqrs-tuvwxyz012345"),
            "PLabcdefghijkmnopqrs-tuvwxyz012345",
        )
        self.assertEqual(
            parse_playlist_id("https://youtu.be/xxxxxxxxx11?list=RDaaaaaaaaaaaaaaaaaaaaaaaaaa012345"),
            "RDaaaaaaaaaaaaaaaaaaaaaaaaaa012345",
        )

    def test_rejects_non_youtube(self):
        with self.assertRaises(RadioError):
            parse_playlist_id("https://example.com/playlist?list=PLaaaaaaaaaaaaaaaaaaaaaaaaaa")

    def test_rejects_missing_list(self):
        with self.assertRaises(RadioError):
            parse_playlist_id("https://www.youtube.com/watch?v=dQw4w9wgGcQ")

    def test_rejects_empty(self):
        with self.assertRaises(RadioError):
            parse_playlist_id("   ")


class StationTests(unittest.TestCase):
    def test_frequency_is_stable(self):
        pid = "PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI"
        self.assertEqual(fm_frequency(pid), fm_frequency(pid))
        self.assertTrue(fm_frequency(pid).replace(".", "", 1).isdigit())

    def test_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "station.json"
            store = StationStore(path)
            station = new_station("PLabcdefghijklmnopqrstuvwx01234567", "https://www.youtube.com/playlist?list=PLabcdefghijklmnopqrstuvwx01234567")
            store.save(station)
            again = StationStore(path)
            self.assertEqual(again.get()["playlist_id"], station["playlist_id"])
            public = public_station(again.get())
            self.assertTrue(public["tuned"])
            self.assertEqual(public["station"]["frequency"], station["frequency"])

    def test_meta_cache_uses_fetcher_once(self):
        calls = []

        def fake(video_id):
            calls.append(video_id)
            return {"id": video_id, "title": "Song", "author": "DJ", "thumbnail": "x", "error": None}

        cache = MetaCache(fetch=fake)
        first = cache.get_many(["dQw4w9wgGcQ"])
        second = cache.get_many(["dQw4w9wgGcQ"])
        self.assertEqual(first[0]["title"], "Song")
        self.assertEqual(second[0]["title"], "Song")
        self.assertEqual(calls, ["dQw4w9wgGcQ"])

    def test_meta_rejects_bad_id(self):
        cache = MetaCache(fetch=lambda video_id: {"id": video_id})
        with self.assertRaises(RadioError):
            cache.get_many(["nope"])


if __name__ == "__main__":
    unittest.main()
