# Python Module: audit.py

`src/modules/audit.py` scans the audio library for duration anomalies and detects full-album continuous rips by cross-referencing local audio lengths against official metadata APIs.

---

## 1. Anomaly Detection Heuristics

Continuous rips masquerading as single songs cause playback errors, broken scrobbles, and unnavigable player lists on DAPs. `audit.py` filters candidates using hard constants:

```python
# From src/modules/audit.py
def audit_long_tracks(
    music_root: str,
    threshold_seconds: float = 600.0,
    json_output: bool = False,
    auto_split: bool = False,
) -> tuple[list[str], int, int, int]:
```

### Verification Criteria
1. **Duration Filter:** Any audio file with duration $\ge 600.0\text{ seconds}$ (10 minutes) is flagged for inspection.
2. **API Cross-Reference:** The track's `(artist, title)` tags are queried against the iTunes Search API (`itunes_track_duration`).
3. **Anomaly Ratio ($> 1.5\times$):**
   $$\text{Ratio} = \frac{\text{Local Duration}}{\text{Expected API Duration}}$$
   If the local file duration exceeds $1.5\times$ the canonical duration (for instance, a local track duration of 2,400s compared to an expected 320s), the track is classified as a **Full-Album Continuous Rip**.

---

## 2. Diagnostic Output & JSON Schema

When executed with `--json`, `audit.py` returns structured JSON on `stdout`:

```json
[
  {
    "path": "/mnt/dap/Music/Pink Floyd/The Wall/disc1.mp3",
    "artist": "Pink Floyd",
    "title": "In The Flesh",
    "album": "The Wall",
    "duration": 2480.5,
    "expected_duration": 196.0,
    "ratio": 12.65,
    "classification": "full_album_rip"
  }
]
```

Human diagnostics and progress meters are written to `stderr` with ANSI styling and Nerd Font icons:
```text
? Scanning for tracks longer than 10 minutes in: /mnt/dap/Music
  • [1/4] Pink Floyd – In The Flesh (41:20 vs expected 3:16) [Ratio: 12.7x] -> Rip detected
```

---

## 3. Automated Expansion Handoff (`--auto-split`)

When invoked with `--auto-split`, `audit.py` captures all confirmed continuous rips and directly invokes `src/modules/album_expander.py` to unbundle them into individual tracks.
