# Python Module: audit.py

`src/modules/audit.py` scans audio libraries for tracks with abnormally long playback durations (>10 minutes) and audits them against official metadata APIs to detect accidental full-album single-file rips.

---

## 1. Capabilities

* **Duration Thresholding:** Identifies all audio tracks exceeding the threshold (default: 600s / 10m).
* **API Cross-Checking:** Queries the Apple iTunes Search API and MusicBrainz to determine the expected duration for the tagged artist and track title.
* **Rip Detection Ratio:**
  * **Ratio > 1.5x:** Flagged as an accidental full-album rip (e.g., an entire 45-minute album rip mistakenly tagged as Track 1).
  * **Ratio < 0.7x:** Flagged as truncated.
* **Auto-Expand Handoff:** Can automatically queue identified full-album rips for unbundling and re-download via `album_expander.py`.

---

## 2. CLI Usage

```bash
# Standard duration audit
python3 src/modules/audit.py -r /path/to/music

# Custom threshold (e.g., 15 minutes = 900 seconds)
python3 src/modules/audit.py -r /path/to/music -t 900

# JSON output of suspect file paths
python3 src/modules/audit.py -r /path/to/music --json
```
