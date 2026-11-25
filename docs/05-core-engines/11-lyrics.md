# Chapter 5.11: Concurrent Synchronized Lyrics Engine (`lyrics.py`)

> **The Syncdap Book Navigation:** [← Previous Section](10-search.md) • [Table of Contents](../index.md) • [Next Section →](12-stats.md)

---

## Pedagogical Context & Prerequisites
In this section, we study `lyrics.py`, which coordinates multithreaded searching, retrieval, sidecar file saving (`.lrc`), and ID3 `USLT`/`SYLT` tag embedding.

---

`src/modules/lyrics.py` searches, normalizes, and downloads synchronized timestamped lyrics (`.lrc`), saving external sidecars for Rockbox and optionally embedding lyrics into audio tags.

---

## 1. Resolution Pipeline

```text
Track Audio File (e.g. 01 Bohemian Rhapsody.flac)
                        │
                        ▼
           Inspect for Existing .lrc Sidecar
            ├── [Exists] Skip network fetch
            └── [Missing]
                        │
                        ▼
           Query LRCLIB API (Exact -> Fuzzy)
            ├── [Hit] Write UTF-8 .lrc Sidecar
            └── [Miss]
                        │
                        ▼
           Invoke syncedlyrics Subprocess
            ├── [Hit] Write UTF-8 .lrc Sidecar
            └── [Miss] Record as Not Found
```

---

## 2. Synchronization Enforcement (`--synced-only`)

Rockbox displays timestamped lyrics line-by-line as the track plays. If an `.lrc` contains un-timestamped plain text, small DAP screens are forced to display static text or blank screens.

When `--synced-only` is active:
- `fetch_lyrics()` checks for the presence of valid timestamps (`[mm:ss.xx]`).
- Plain text lyrics without timing brackets are **rejected**, ensuring only verified synchronized lyrics are saved.

---

## 3. Embedded Tag Injection

When invoked with `--embed`, lyrics are written into audio container tags:
- **MP3:** ID3v2 `USLT` (Unsynchronized lyrics) or `SYLT` (Synchronized lyrics) frames.
- **FLAC / OGG:** Vorbis comment `LYRICS` block.
- **M4A / MP4:** QuickTime `©lyr` atom.

---

## 4. CLI Invocations

```bash
# Fetch missing synced lyrics across library
syncdap lyrics fetch -r /mnt/dap/Music --synced-only

# Fetch and embed lyrics into audio tags
syncdap lyrics fetch -r /mnt/dap/Music --embed

# Non-destructive simulation
syncdap lyrics fetch -r /mnt/dap/Music --dry-run
```

---

## Summary & Next Steps
To conclude Chapter 5, we inspect `stats.py`, which provides high-level analytics and Rockbox health diagnostic audits.

---

> **The Syncdap Book Navigation:** [← Previous Section](10-search.md) • [Table of Contents](../index.md) • [Next Section →](12-stats.md)
