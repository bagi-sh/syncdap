# Python Module: dedup.py

`src/modules/dedup.py` scans audio libraries for duplicate tracks, retains the highest audio quality copy, purges inferior duplicates, and relinks playlists.

---

## 1. Capabilities

* **Quality Tiering:** Prioritizes retention using a strict hierarchy:
  1. Lossless FLAC / WAV
  2. High-bitrate lossy (320kbps MP3 / 256kbps AAC M4A)
  3. Lower-bitrate lossy
* **Metadata Normalization:** Matches tracks by cleaned title, artist, and playback duration rather than simple filename comparison.
* **Playlist Relinking:** Automatically updates all `.m3u` and `.m3u8` playlists referencing deleted duplicate paths to point to the surviving high-quality track.

---

## 2. CLI Usage

```bash
# Scan and deduplicate library
python3 src/modules/dedup.py -r /path/to/music

# Dry-run simulation (prints what would be deleted without modifying files)
python3 src/modules/dedup.py -r /path/to/music --dry-run
```
