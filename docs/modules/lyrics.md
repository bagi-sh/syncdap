# Python Module: lyrics.py

`src/modules/lyrics.py` searches, downloads, and embeds synchronized `.lrc` lyrics for audio files.

---

## 1. Capabilities

* **Timestamped Search:** Scans album directories for tracks lacking `.lrc` files and fetches synchronized lyrics from LRCLIB.
* **Format Filtering:** Supports `--synced-only` to reject plain, un-timestamped lyrics in favor of time-coded lines (`[mm:ss.xx]`).
* **Rockbox-Native Placement:** Writes `<track_filename>.lrc` side-by-side with each audio track for direct display on Rockbox.
* **Tag Embedding:** Supports embedding lyrics text directly into ID3 `USLT`/`SYLT` frames or Vorbis comments via `--embed`.

---

## 2. CLI Usage

```bash
# Fetch missing .lrc files
python3 src/modules/lyrics.py album_dirs.txt 4 false

# Fetch strictly synchronized lyrics
python3 src/modules/lyrics.py album_dirs.txt 4 true

# Fetch and embed directly into audio tags
python3 src/modules/lyrics.py album_dirs.txt 4 true --embed
```
