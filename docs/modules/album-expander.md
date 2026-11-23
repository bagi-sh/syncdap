# Python Module: album_expander.py

`src/modules/album_expander.py` unbundles single-file full-album rips (e.g. YouTube "Full Album" audio rips or single continuous vinyl/CD dumps) into authentic, individually tagged audio tracks.

---

## 1. Architectural Role & Execution Lifecycle

When `syncdap album expand <file>` or `syncdap library audit --auto-split` identifies a single-file rip:

```text
Continuous Rip File (e.g. full_album.mp3, >600s)
                         │
                         ▼
        Read Existing Tags & Directory Context
                         │
                         ▼
       Resolve Tracklist via iTunes / MusicBrainz
           (Tracks, Titles, Canonical Durations)
                         │
                         ▼
       Parallel Ingestion of Individual Tracks
        (via fallback.py / yt-dlp Candidate Matching)
                         │
                         ▼
       Enforce Rockbox ID3v2.3 Tags & cover.jpg
                         │
                         ▼
       Relink Playlists & Safely Remove Obsolete Rip
```

---

## 2. Tracklist Specification & Schema

Tracklists are parsed into strongly-typed `TrackSpec` dataclasses:

```python
# From src/modules/album_expander.py
@dataclass
class TrackSpec:
    number: int
    title: str
    artist: str
    album: str
    album_artist: str
    duration_sec: float
    year: str = ""
    genre: str = ""
    cover_url: str = ""
    disc_number: int = 1
    total_tracks: int = 1
```

---

## 3. Replacement Safety & Crash Guarantees

Unbundling an album must never destroy user data prematurely:
1. **Verification Before Deletion:** Every individual track is downloaded, transcoded, and inspected with `mutagen.File()` to verify audio integrity (`is_valid_audio()`).
2. **Threshold Verification:** If fewer than 80% of canonical tracks are successfully resolved and verified, the single-file rip is **strictly preserved**, and an error warning is emitted.
3. **Playlist Entry Migration:** If playlists referenced the old single-file rip, `expand_playlist_entries()` replaces the single line with the sequential list of expanded track paths.
4. **Atomic Purge:** The continuous rip is deleted only after all individual tracks and playlists have been written and flushed to disk.

---

## 4. CLI Invocations

```bash
# Expand a specific rip file
python3 src/modules/album_expander.py "/mnt/dap/Music/Pink Floyd/Dark Side of the Moon/full_album.mp3"

# Expand with 8 concurrent download threads
python3 src/modules/album_expander.py -t 8 "/mnt/dap/Music/Artist/Album/rip.mp3"

# Non-destructive simulation
python3 src/modules/album_expander.py --dry-run "/mnt/dap/Music/Artist/Album/rip.mp3"
```
