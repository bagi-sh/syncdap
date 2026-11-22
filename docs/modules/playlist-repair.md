# Python Module: playlist_repair.py

`src/modules/playlist_repair.py` audits `.m3u` and `.m3u8` playlists, relinking moved or renamed audio files and pruning broken links.

---

## 1. Capabilities

* **Link Audit:** Reads all entries in playlist files across the library and verifies their existence on disk.
* **Fuzzy Relinking:** When an entry points to a missing file (e.g., due to transcoding from `.flac` to `.mp3` or renaming), it scans the library using normalized titles and artist names to locate the relocated file.
* **Dead Link Pruning:** Removes non-recoverable broken paths from playlists.
* **Simulation Mode:** Supports `--dry-run` to preview all proposed path modifications.

---

## 2. CLI Usage

```bash
# Repair and relink all playlists in library
python3 src/modules/playlist_repair.py -r /path/to/music

# Dry-run inspection
python3 src/modules/playlist_repair.py -r /path/to/music --dry-run
```
