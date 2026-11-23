# Python Module: fallback.py

`src/modules/fallback.py` implements the autonomous track rescue engine, utilizing `yt-dlp` to recover audio tracks that failed during primary spotDL ingestion or encountering regional stream blocks.

---

## 1. Candidate Filtering Engine

When querying YouTube search results (`ytsearch10:`), `fallback.py` applies hard regex pattern guards to reject invalid audio:

```python
# From src/share/constants.py
FULL_ALBUM_PATTERNS = [
    r'\b(full[\s\-_]*album)\b',
    r'\b(album[\s\-_]*completo)\b',
    r'\b(complete[\s\-_]*album)\b',
    r'\b(discography)\b',
    r'\b(greatest\s+hits(\s+full)?)\b',
]

LIVE_PATTERNS = [
    r'\b(ao[\s\-_]*vivo)\b',
    r'\b(live(\s+(at|in|from|version|session|acoustic))?)\b',
    r'\b(bootleg)\b',
]

REMIX_PATTERNS = [
    r'\b(re[\s\-_]*mix(ed)?)\b',
    r'\b(slowed(\s+(and|\+)\s+reverb)?)\b',
    r'\b(sped[\s\-_]*up)\b',
    r'\b(nightcore)\b',
    r'\b(8d\s+audio)\b',
]
```

### Candidate Scoring Function
Each candidate starts with a score of 0:
- **Disqualification (-9999):** Any match with `FULL_ALBUM_PATTERNS`.
- **Duration Proximity:** Candidates within $\pm 4.0\text{ seconds}$ receive $+150$ points; within $10\%$ receive $+80$ points. Larger discrepancies are penalized proportionally.
- **Channel Trust:** Topic channels (e.g. `Queen - Topic`) or official VEVO accounts receive $+100$ points.

---

## 2. Audio Extraction & Mutagen Tag Synthesis

1. **Extraction:** Audio streams are extracted to a temporary folder using `yt-dlp` and `ffmpeg` with audio quality set to 0 (best VBR/CBR).
2. **Metadata Writing:** YouTube's arbitrary stream metadata is completely wiped. Canonical tags from iTunes or MusicBrainz are written via `write_audio_metadata()`:
   - `TIT2` (Title), `TPE1` (Artist), `TALB` (Album), `TPE2` (Album Artist).
   - `TRCK` (Track Number / Total Tracks), `TDRC` (Year), `TCON` (Genre).
3. **Rockbox Compliance:** Tags are written in ID3v2.3 format with UTF-16 encoding.

---

## 3. CLI Invocations

```bash
# Rescue tracks from a failed spotDL error log
python3 src/modules/fallback.py -l erros.spotdl -r /mnt/dap/Music

# Rescue an individual song directly
python3 src/modules/fallback.py --artist "Pink Floyd" --title "Time" -r /mnt/dap/Music
```
