# R&T — Radio & Tube

Local YouTube playlist radio. Paste a playlist link, hit **Link**, then **Tune In**.
The station loops the list in your browser through the official YouTube embed — nothing is downloaded.

## Start

```bash
python3 -m rt
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). Python 3.10+ is enough (stdlib only).

Listen from a phone on the same Wi-Fi:

```bash
python3 -m rt --host 0.0.0.0
```

Pre-tune a playlist:

```bash
python3 -m rt --playlist 'https://www.youtube.com/playlist?list=PLxxxxxxxx'
```

## How it plays

1. The local server stores the playlist id and remembers shuffle/loop.
2. The page loads that playlist with the YouTube IFrame Player API.
3. Playback continues down the list, then repeats, like leaving a radio on.

Keyboard: <kbd>Space</kbd> play/pause, <kbd>n</kbd> next, <kbd>p</kbd> previous.

## Tests

```bash
python3 -m unittest discover -s rt/tests -v
```
