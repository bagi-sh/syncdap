# External API: yt-dlp Stream Engine

`src/modules/fallback.py` uses `yt-dlp` as a stream extraction and media recovery engine.

---

## 1. Responsibilities

* **Metadata-Guided Recovery:** When spotDL fails to locate or download a track, `fallback.py` extracts search terms (artist, track title, expected duration) and queries YouTube/YouTube Music streams via `yt-dlp`.
* **Duration Sanity Check:** Compares stream duration to official metadata to prevent downloading truncated previews or bloated multi-hour live compilations.
* **Audio Transcoding:** Pipes extracted streams through `ffmpeg` to match the target format specified by `--format` (`flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`).
