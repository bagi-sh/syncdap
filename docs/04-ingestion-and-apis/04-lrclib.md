# Chapter 4.4: LRCLIB & Syncedlyrics: Synchronized Lyrics (.lrc)

> **The Syncdap Book Navigation:** [← Previous Section](03-musicbrainz.md) • [Table of Contents](../index.md) • [Next Section →](05-lastfm.md)

---

## Pedagogical Context & Prerequisites
In this section, we explore the timestamped lyric retrieval pipeline, utilizing LRCLIB's REST API and `syncedlyrics` fallback routines.

---

`src/share/lyrics.py` implements a 2-stage retrieval pipeline using the open **LRCLIB** database, backed by a subprocess fallback to `syncedlyrics`, generating synchronized timestamped `.lrc` files for Rockbox on-screen lyric playback.

---

## 1. Network Protocol & Query Parameters

- **Base Endpoint:** `https://lrclib.net/api/`
- **User-Agent:** `MusicLyricsFetcher/1.0`
- **Timeout:** `5` seconds (`urllib.request.urlopen(req, timeout=5)`)
- **Encoding:** Strict UTF-8 without BOM.

---

## 2. Two-Stage Resolution Protocol

When fetching lyrics for a track, `fetch_lyrics()` executes two sequential search strategies before resorting to external scrapers:

```text
Track Metadata (Artist, Title, Album, Duration)
                      │
                      ▼
 Stage 1: Exact GET Query (/api/get)
   Parameters: artist_name, track_name, album_name, duration (rounded to int)
   ├── [Hit] Synced lyrics found -> Write .lrc -> Return 'synced'
   └── [Hit] Plain lyrics found & !synced_only -> Write .lrc -> Return 'plain'
                      │
                      ▼ (If 404 Not Found or Network Error)
 Stage 2: Fuzzy Search Query (/api/search)
   Parameters: q="<artist> <title>"
   ├── Iterates results for first syncedLyrics match -> Write .lrc -> Return 'synced'
   └── If !synced_only, takes first plainLyrics match -> Write .lrc -> Return 'plain'
                      │
                      ▼ (If no results)
 Stage 3: Subprocess Fallback (syncedlyrics CLI)
   Executes: syncedlyrics "<artist> - <title>" -o "<out_path>"
```

### Grounded Source Implementation
```python
# From src/share/lyrics.py
def fetch_lyrics(artist: str, title: str, album: str = "", duration: float | None = None,
                 out_path: str = "", synced_only: bool = False):
    if not artist or not title or not out_path:
        return None

    # Stage 1: Exact Query
    params = {'artist_name': artist, 'track_name': title}
    if album:
        params['album_name'] = album
    if duration:
        params['duration'] = round(duration)

    try:
        url = 'https://lrclib.net/api/get?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'MusicLyricsFetcher/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            synced = data.get('syncedLyrics')
            plain = data.get('plainLyrics')
            if synced:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(synced.strip() + '\n')
                return 'synced'
            elif not synced_only and plain:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(plain.strip() + '\n')
                return 'plain'
    except Exception:
        pass
```

---

## 3. Timestamp Invariants & Format Specification

LRCLIB returns lines adhering to the enhanced LRC specification:
```text
[00:12.34] Look into my eyes and see
[00:15.89] What you mean to me
```
- **Bracket Format:** Exactly `[mm:ss.xx]` or `[mm:ss.xxx]`.
- **Hardware Contract:** Rockbox requires the `.lrc` file to be named identically to the audio file in the same folder:
  ```text
  /Music/Queen/A Night at the Opera/01 Death on Two Legs.mp3
  /Music/Queen/A Night at the Opera/01 Death on Two Legs.lrc
  ```
- **`synced_only` Contract:** When `--synced-only` is passed, `fetch_lyrics()` refuses to write unsynchronized plain text, avoiding static wall-of-text displays on small DAP LCD screens.

---

## Summary & Next Steps
To complete our survey of external APIs, we examine the Last.fm Desktop Web Authentication flow and scrobble submission protocol.

---

> **The Syncdap Book Navigation:** [← Previous Section](03-musicbrainz.md) • [Table of Contents](../index.md) • [Next Section →](05-lastfm.md)
