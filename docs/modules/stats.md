# Python Module: stats.py

`src/modules/stats.py` inspects the audio library, calculating comprehensive metrics on audio formats, bitrates, synchronized lyrics coverage, artwork status, and Rockbox compliance.

---

## 1. Metrics Collected & Analytics Model

When traversing the music root, `stats.py` analyzes:
- **Audio Codec Distribution:** Total counts and storage breakdown across `.mp3`, `.flac`, `.m4a`, `.opus`, `.ogg`, and `.wav`.
- **Bitrate Analysis:** Categorizes tracks into Lossless ($\ge 800\text{ kbps}$), High Quality ($256\text{–}320\text{ kbps}$), Medium ($160\text{–}224\text{ kbps}$), and Low ($< 160\text{ kbps}$).
- **Rockbox Readiness:** Checks percentage of albums possessing external `cover.jpg` vs. heavy embedded artwork, and tracks missing `ALBUMARTIST`.
- **Lyrics Coverage:** Percentage of tracks accompanied by timestamped `.lrc` sidecars.

---

## 2. Output Formats

### Formatted ANSI Dashboard (Default)
Emits an interactive terminal dashboard featuring Unicode progress bars:
```text
Total Library Size: 45.2 GB (3,412 tracks across 284 albums)
Playtime: 9 days, 14 hours

Format Breakdown:
  FLAC:   [████████████████░░░░]  78.4% (2,675 tracks, 38.1 GB)
  MP3:    [████░░░░░░░░░░░░░░░░]  21.6% (  737 tracks,  7.1 GB)

Metadata Health:
  ✓ External cover.jpg:  98.2% of albums
  ✓ Synchronized .lrc:   91.4% of tracks
  ✓ Canonical ALBUMARTIST: 99.7% of tracks
```

### Machine-Readable JSON (`--json`)
```json
{
  "total_tracks": 3412,
  "total_albums": 284,
  "total_size_bytes": 48532918272,
  "total_duration_sec": 828000.0,
  "formats": {
    "flac": {"count": 2675, "size_bytes": 40910000000},
    "mp3": {"count": 737, "size_bytes": 7622918272}
  },
  "lrc_coverage_pct": 91.4,
  "covers_optimized_pct": 98.2
}
```

---

## 3. CLI Invocations

```bash
# View dashboard for music directory
syncdap library status -r /mnt/dap/Music

# Output machine-readable JSON
syncdap library status -r /mnt/dap/Music --json
```
