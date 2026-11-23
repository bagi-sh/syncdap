# Shell Coordinator: downloader.sh

`src/sh/downloader.sh` manages external media ingestion from Spotify URLs using **spotDL**, controlling format parameters, directory structures, and error logging for downstream rescue.

---

## 1. Execution Contract & Invocation Pipeline

When `syncdap download <URL>` is called, `src/sh/orchestrator.sh` delegates to `run_spotdl_download()`.

```text
Target Spotify URL (Track / Album / Playlist)
                      │
                      ▼
            run_spotdl_download()
                      │
                      ├─► spotDL Subprocess Execution
                      │     ├── Bitrate & Target Format (-F / --format)
                      │     ├── Tag / Cover Fetching
                      │     └── Path Formatting: {artist}/{album}/{track-number} {title} - {artist}
                      │
                      ├─► Playlist Detection ([[ "$CLEAN_URL" =~ /playlist/ ]])
                      │     └── Appends: --m3u "{list}.m3u8"
                      │
                      └─► Failure Interception & Error Logging
                            └── Captures failed tracks into erros.spotdl
```

---

## 2. spotDL Command Architecture & Hardcoded Defaults

The execution array is strictly isolated to prevent argument injection:

```bash
# Excerpt from src/sh/downloader.sh
local spotdl_cmd=(
    run_spotdl
    "$CLEAN_URL"
    "${SPOTDL_FORMAT_ARGS[@]}"
    --threads "$THREADS"
    --output "{artist}/{album}/{track-number} {title} - {artist}.{output-ext}"
    --detect-formats mp3 flac m4a ogg opus wav
    --scan-for-songs
    --overwrite skip
    --generate-lrc
    --audio youtube youtube-music soundcloud bandcamp
    --max-retries 1
    --save-errors erros.spotdl
    --respect-skip-file
    --yt-dlp-args "--cookies-from-browser firefox --throttled-rate 100K"
)
```

### Critical Parameters Verified from Source
- **Audio Providers (`--audio`):** `youtube youtube-music soundcloud bandcamp`. Prioritizes YouTube Music before falling back to Soundcloud or Bandcamp.
- **Deduplication / Skip (`--overwrite skip --respect-skip-file`):** If a file already exists on disk in the target format, spotDL skips the re-download immediately.
- **Format Discovery (`--detect-formats mp3 flac m4a ogg opus wav`):** Recognizes existing tracks regardless of whether they match the current target format, preventing duplicate downloads in mixed libraries.
- **Throttling Defense (`--yt-dlp-args`):** Injects `--cookies-from-browser firefox --throttled-rate 100K` to bypass YouTube bot challenge heuristics and avoid account/IP bans.
- **Lyrics Auto-generation (`--generate-lrc`):** Instructs spotDL to emit synchronized `.lrc` files alongside the audio file.

---

## 3. Error Handling & Hand-off to Rescue Subsystem

1. **Error Persistence:** `rm -f erros.spotdl` runs immediately prior to execution. If spotDL fails on individual tracks (e.g. rate limit, regional blocking, or YouTube 403), it appends failed Spotify URLs into `erros.spotdl`.
2. **Non-Fatal Shell Interception:** spotDL is invoked with:
   ```bash
   "${spotdl_cmd[@]}" || true
   ```
   This ensures that partial download failures do not abort the shell script with an unhandled exit code.
3. **Rescue Triggering:** In `src/sh/orchestrator.sh`, the orchestrator inspects `erros.spotdl`. If non-empty, it automatically invokes `src/modules/fallback.py` to rescue the missing songs via direct `yt-dlp` scraping and metadata synthesis.
