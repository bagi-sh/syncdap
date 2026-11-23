# External API: yt-dlp Stream & Fallback Engine

`src/modules/fallback.py` uses **yt-dlp** as an automated media rescue engine to recover missing or blocked tracks when Spotify/spotDL fails.

---

## 1. Candidate Search & Query Grammar

When rescuing a track, `fallback.py` constructs a targeted YouTube search query:
```bash
ytsearch10:"<Artist> - <Title>"
```
Querying the top 10 candidates ensures broad coverage across official topic channels, music videos, and user uploads.

---

## 2. Candidate Filtering & Scoring Algorithm

To avoid downloading audio from live concerts, amateur covers, nightcore remixes, or full-album compilations, `score_video_candidate()` evaluates each candidate:

```python
# Excerpt from src/modules/fallback.py
def score_video_candidate(cand: dict, artist: str, title: str, expected_dur: float | None = None,
                          allow_live: bool = False, allow_remix: bool = False) -> int:
    score = 0
    c_title = (cand.get('title') or '').lower()
    channel = (cand.get('channel') or cand.get('uploader') or '').lower()
    dur = cand.get('duration') or 0

    # 1. Immediate Disqualification: Full-Album Rips
    for pat in FULL_ALBUM_PATTERNS:
        if re.search(pat, c_title, re.IGNORECASE):
            return -9999

    # 2. Live & Remix Penalties
    if not allow_live:
        for pat in LIVE_PATTERNS:
            if re.search(pat, c_title, re.IGNORECASE):
                return -500
    if not allow_remix:
        for pat in REMIX_PATTERNS:
            if re.search(pat, c_title, re.IGNORECASE):
                return -500

    # 3. Duration Matching (Within 4 seconds or 10%)
    if expected_dur and dur > 0:
        diff = abs(dur - expected_dur)
        if diff <= 4.0:
            score += 150
        elif diff <= (expected_dur * 0.10):
            score += 80
        else:
            score -= int(diff * 5)

    # 4. Official Channel Verification
    if 'topic' in channel or 'vevo' in channel or artist.lower() in channel:
        score += 100

    return score
```

---

## 3. Transcoding & Tag Synthesis Pipeline

Once the highest scoring candidate is selected:
1. **Extraction:** yt-dlp extracts audio using `ffmpeg` without video stream overhead:
   ```bash
   yt-dlp --extract-audio --audio-format "$TARGET_FORMAT" --audio-quality 0 \
          --output "$TEMP_DIR/download.%(ext)s" \
          --cookies-from-browser firefox \
          "https://www.youtube.com/watch?v=..."
   ```
2. **Metadata Injection (`src/share/audio.py`):** yt-dlp metadata is discarded. `fallback.py` writes clean ID3v2.3 tags (`artist`, `title`, `album`, `albumartist`, `year`, `track_number`) retrieved from iTunes/MusicBrainz.
3. **Lyrics & Artwork Hook:** Downloads official cover artwork via `src/share/covers.py` and fetches `.lrc` timestamped lyrics from LRCLIB.
4. **Atomic Placement:** Moves the completed, tagged file to its final destination in `/Music/<Artist>/<Album>/`.
