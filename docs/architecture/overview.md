# Architecture Overview

`syncdap` uses a modular two-tier architecture: **Bash Shell Coordinators** for environment management, signal handling, and argument routing, combined with **Python Processing Engines** for media analysis, metadata parsing, and API integration.

```text
                                  User Invocations
                                        │
                                        ▼
                               syncdap (Entrypoint)
                                        │
       ┌────────────────────────────────┴────────────────────────────────┐
       ▼                                                                 ▼
CLI Grammar & Parsing (src/sh/cli.sh)                Configuration & State (src/sh/config.sh)
       │
       ▼
Orchestration Coordinator (src/sh/orchestrator.sh)
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼                                 ▼                                 ▼
External Media Ingestion          Dedicated Domain Engines        Tag & Metadata Standardization
(spotDL / yt-dlp / ffmpeg)         (Patch / Playlists / Romaji)   (Rockbox Tags / Covers / Lyrics)
       │                                 │                                 │
       └─────────────────────────────────┼─────────────────────────────────┘
                                         ▼
                             Underlying File System / DAP
                                 (/mnt/dap or ./Music)
```

---

## 1. Two-Tier Execution Model

### The Shell Coordinator Tier (`src/sh/`)
* **Minimal dependencies:** Relies solely on standard POSIX/GNU Linux utilities.
* **Process isolation:** Manages runtime temp directories, trap handlers (`cleanup EXIT INT TERM`), and child processes.
* **CLI UX discipline:** Enforces consistent argument parsing, exit codes (`0`, `1`, `2`), and Dual-Audience error formatting.

### The Python Engine Tier (`src/modules/` & Domain Packages)
* **High-performance audio inspection:** Powered by `mutagen` and `eyed3`.
* **API clients:** Multithreaded queries to iTunes, Deezer, LRCLIB, and MusicBrainz.
* **Firmware optimization rules:** Enforces Rockbox database invariants (such as `ALBUMARTIST` normalization, ID3v2.3 tag compatibility, and external `cover.jpg` extraction).

---

## 2. Directory Layout & Boundaries

```text
src/
├── sh/                   # Shell scripts: entrypoint dispatch, temp traps, CLI formatting
│   ├── cli.sh            # Argument parsing, --help generator, POSIX flag extraction
│   ├── orchestrator.sh   # High-level pipeline coordination (library, artist, album, track)
│   ├── downloader.sh     # Wrapper around spotDL and stream downloaders
│   ├── playlists.sh      # Post-download playlist normalization and DAP path mapping
│   ├── common.sh         # Global variables, color definitions, dependency validation
│   ├── icons.sh          # Monochromatic Nerd Font & Safe Unicode detection
│   └── config.sh         # Persistent user configuration management
│
├── modules/              # Standalone Python processing engines
│   ├── stats.py          # Library health and audio format analytics
│   ├── audit.py          # Track duration discrepancy auditing (>10m tracks)
│   ├── album_expander.py # Unbundling single-file album rips into tracks
│   ├── covers.py         # Standalone cover.jpg extraction and embedded art removal
│   ├── dedup.py          # Audio deduplication prioritizing lossless audio
│   ├── fallback.py       # Stream recovery using yt-dlp fallback
│   ├── genres.py         # Multi-API genre enrichment
│   ├── lyrics.py         # Timestamped .lrc retrieval and tag embedding
│   ├── playlist_repair.py# Relinking moved/renamed audio files in playlists
│   ├── rockbox_tags.py   # Split-album prevention & tag normalization
│   └── search.py         # Track and album metadata search via iTunes/MusicBrainz
│
├── patch/                # Audio transcoding and quality upgrade subsystem
├── playlists/            # Interactive playlist manager and merger
├── romaji/               # Japanese Kanji/Kana transliteration engine
└── share/                # Shared utilities across all Python engines
```

---

## 3. Data Flow: An Example Pipeline (`syncdap library optimize`)

When running a full optimization:
1. `syncdap` parses options and delegates to `orchestrate_library "optimize"`.
2. `orchestrator.sh` runs `orchestrate_dedup`: scans for duplicates, removes lower-bitrate duplicates, and updates playlists.
3. `orchestrate_covers "optimize"` invokes `src/modules/covers.py`: extracts embedded images to `cover.jpg` per album folder and strips embedded artwork tags to save DAP memory.
4. `orchestrate_tags "fix"` invokes `src/modules/rockbox_tags.py`: inspects every album folder, standardizing `ALBUM` and `ALBUMARTIST` to prevent Rockbox from splitting albums.
5. `orchestrate_playlist "repair"` invokes `src/modules/playlist_repair.py`: audits all `.m3u`/`.m3u8` files, updating renamed paths and pruning dead links.
6. Temporary working files are purged via `trap cleanup EXIT`.
