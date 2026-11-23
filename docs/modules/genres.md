# Python Module: genres.py

`src/modules/genres.py` standardizes and populates missing genre tags across the music library by querying a 3-tier cascade of online metadata APIs.

---

## 1. Multi-Tier Resolution Cascade

Because single APIs frequently lack genre tags for obscure or classical releases, `genres.py` uses a cascaded resolver:

```text
Album Folder (/Music/<Artist>/<Album>/)
                    │
                    ▼
          Query Tier 1: iTunes Search API
            ├── [Hit] Return primaryGenreName
            └── [Miss]
                    │
                    ▼
          Query Tier 2: Deezer API
            ├── [Hit] Return album/artist genre
            └── [Miss]
                    │
                    ▼
          Query Tier 3: MusicBrainz Web Service
            ├── [Hit] Extract top-voted community tag
            └── [Miss] Return None
```

### In-Memory Cache Protocol
To eliminate redundant HTTP traffic across multi-track albums, queries are keyed by `(artist, album)`:
```python
# From src/share/api.py
_genre_cache: dict[str, str | None] = {}

def resolve_online_genre(artist: str, album: str) -> str | None:
    key = f"{artist.strip().lower()} - {album.strip().lower()}"
    if key in _genre_cache:
        return _genre_cache[key]
    # Execute cascade...
```

---

## 2. In-Place Tag Injection

When a canonical genre is resolved (e.g. "Progressive Rock"):
- `genres.py` updates every audio file in the album folder.
- Formats handled: MP3 (`TCON`), FLAC (`GENRE`), M4A (`©gen`), and OGG/Opus (`GENRE`).
- If an album already possesses valid, non-empty genre tags across all tracks, it is skipped immediately (`already_set_albums`).

---

## 3. CLI Invocations

```bash
# Enrich genres across entire DAP library with 4 threads
syncdap tags genres -r /mnt/dap/Music -t 4

# Preview proposed genre modifications without writing tags
syncdap tags genres -r /mnt/dap/Music --dry-run
```
