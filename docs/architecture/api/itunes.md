# External API: iTunes Search & Lookup API

`syncdap` queries the Apple iTunes Search and Lookup API (`src/share/api.py`) for high-speed, unauthenticated metadata resolution, canonical track duration verification, and high-resolution album artwork.

---

## 1. Network Protocol & Hardcoded Invariants

- **Endpoints:**
  - Search: `https://itunes.apple.com/search`
  - Lookup: `https://itunes.apple.com/lookup`
- **HTTP Method:** `GET`
- **Headers:** `User-Agent: SyncDAP/1.0`
- **Timeout:** Exactly `8` seconds (`urllib.request.urlopen(req, timeout=8)`)
- **Rate Limit Policy:** Apple throttles excessive bursts. `syncdap` bounds concurrency and limits `limit=5` per query to minimize bandwidth.

---

## 2. Query Architecture & Parameters

### 1. Track Search (`itunes_search`)
Used by `src/modules/search.py` and `src/modules/audit.py`:
```text
GET https://itunes.apple.com/search?term=<artist>+<title>&entity=song&limit=5&media=music
```
- `term`: URL-encoded query string. Parenthetical annotations and feature tags (e.g. `(feat. Drake)`) are stripped via `clean_term()` before encoding.
- `entity`: Constrained to `song`, `album`, or `musicArtist`.
- `media`: Constrained to `music` to exclude podcasts and audiobooks.

### 2. Collection Tracklist Lookup (`itunes_lookup_collection`)
Used by `src/modules/album_expander.py` to unbundle single-file rips:
```text
GET https://itunes.apple.com/lookup?id=<collection_id>&entity=song
```
Returns complete album metadata including multi-disc positions, track counts, and release years.

---

## 3. High-Resolution Artwork URL Rewriting

The default iTunes payload returns thumbnail image URLs constrained to `100x100` pixels:
```json
{
  "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/Music115/.../100x100bb.jpg"
}
```

Because modern DAP screens and Rockbox album views require higher resolutions without pixelation, `syncdap` dynamically transforms the URL:
```python
# From src/share/api.py
cover = r.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
```
For DAP storage, `600x600` is the optimal sweet spot: it renders crisply on 240x240 and 320x240 displays while keeping JPEG filesize under 150 KB, preventing DAP out-of-memory errors.

---

## 4. Track Duration Matching Logic

In `itunes_track_duration()`, durations are validated against local audio lengths to detect full-album rips:
```python
# From src/share/api.py
def itunes_track_duration(artist: str, title: str) -> float | None:
    for r in itunes_search(f'{artist} {title}', entity='song', limit=5):
        r_artist = r.get('artistName', '').lower()
        dur_ms = r.get('trackTimeMillis')
        if dur_ms and (artist.lower() in r_artist or r_artist in artist.lower()):
            return dur_ms / 1000.0
    return None
```
- Returns canonical duration as a floating-point number in seconds.
- Enforces bidirectional artist substring matching (`artist in r_artist or r_artist in artist`) to prevent false positives from generic song titles (e.g., "Intro" or "Home").
