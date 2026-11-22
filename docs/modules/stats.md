# Python Module: stats.py

`src/modules/stats.py` is the library analytics, format distribution, and Rockbox health dashboard engine.

---

## 1. Capabilities

* **Storage & Audio Metrics:** Scans target paths and reports total audio files, disk usage, and storage allocation.
* **Audio Format Breakdown:** Categorizes files by container (`FLAC`, `MP3`, `M4A`, `OPUS`, `OGG`, `WAV`) and identifies high-resolution 24-bit audio.
* **Rockbox Health Audit:**
  * Checks for missing `ALBUMARTIST` tags (preventing split albums).
  * Audits cover art distribution (standalone `cover.jpg` vs. embedded art).
  * Checks lyrics availability and synchronized `[mm:ss]` percentage.
  * Identifies 0-byte ghost files.

---

## 2. CLI Usage

```bash
# Human-readable table dashboard
python3 src/modules/stats.py -r /path/to/music

# Machine-readable JSON output
python3 src/modules/stats.py -r /path/to/music --json

# Plain tab-delimited summary for Unix pipes
python3 src/modules/stats.py -r /path/to/music --plain
```
