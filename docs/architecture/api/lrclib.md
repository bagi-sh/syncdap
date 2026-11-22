# External API: LRCLIB & Synced Lyrics

`syncdap` fetches synchronized timestamped lyrics (`.lrc`) using the LRCLIB open database and `syncedlyrics`.

---

## 1. Endpoints & Protocol

* **LRCLIB Base URL:** `https://lrclib.net/api/get`
* **Parameters:** `artist_name`, `track_name`, `album_name`, `duration`.
* **Synced Lyrics Extraction:** Filters strictly for line-by-line timestamped tags (`[mm:ss.xx]`) when `--synced-only` is active.

---

## 2. Usage in syncdap

* **Standalone File Generation (`src/modules/lyrics.py`):** Saves `<track_name>.lrc` in the same directory as the audio file for native Rockbox on-screen display.
* **Tag Embedding:** Embeds synchronized lyrics directly into audio file tags (`USLT` / `SYLT` ID3 frames or Vorbis comments) for DAPs with embedded lyrics support.
