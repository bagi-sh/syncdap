# Python Module: fallback.py

`src/modules/fallback.py` is the resilient yt-dlp metadata recovery and stream extraction engine.

---

## 1. Capabilities

* **Rescue Pipeline:** Ingests failed track URLs or metadata batches (e.g., from `erros.spotdl`).
* **Search Matching:** Queries multiple search providers to locate matching studio audio streams.
* **Duration Enforcement:** Prevents truncated audio or bloated live recordings by enforcing duration tolerance thresholds against target metadata.
* **Transcoding:** Pipes streams directly into `ffmpeg` to match the target audio format.

---

## 2. CLI Usage

```bash
python3 src/modules/fallback.py \
    batch_metadata.spotdl \
    /tmp/syncdap_session \
    "" \
    4 \
    false \
    flac \
    ""
```
