# syncdap Documentation Hub

Welcome to the `syncdap` documentation! `syncdap` is a dedicated synchronization coordinator, metadata optimizer, and audio maintenance suite designed for **Rockbox firmware** and audiophile Digital Audio Players (DAPs).

---

## Documentation Structure

```text
docs/
├── getting-started/       # Setup, prerequisites, hardware mount points, configuration
├── architecture/          # End-to-end design, shell coordinators, API clients, hardware models
├── modules/               # Detailed documentation for each internal Python engine
└── reference/             # Complete CLI reference by resource and exit code specifications
```

---

## 1. Getting Started

Essential guides to get `syncdap` running on your system and connected to your DAP:

* **[Installation Guide](getting-started/installation.md):** System requirements (`ffmpeg`, `yt-dlp`, `uv`), cloning, updates, and uninstallation.
* **[Configuration Guide](getting-started/configuration.md):** Persistent configuration (`~/.config/syncdap/config`), setting up DAP mount points, and configuring Nerd Font symbols.

---

## 2. Architecture & Design

Understand how `syncdap` coordinates media processing across bash and Python:

* **[Architecture Overview](architecture/overview.md):** Multi-stage execution pipeline, process isolation, and the boundary between shell coordinators and Python engines.
* **[Shell Coordinators](architecture/shell/cli.md):** Deep dives into each script in `src/sh/`:
  * [`cli.sh`](architecture/shell/cli.md) – Grammar parser, help generator, option routing.
  * [`orchestrator.sh`](architecture/shell/orchestrator.md) – Execution coordinator and workflow pipelines.
  * [`downloader.sh`](architecture/shell/downloader.md) – spotDL wrapper and recovery traps.
  * [`common.sh`](architecture/shell/common.md) – Runtime environment, signal handlers, temp directory lifecycle.
  * [`playlists.sh`](architecture/shell/playlists.md) – Playlist path normalization and sync.
  * [`icons.sh`](architecture/shell/icons.md) – Nerd Font detection and monochromatic glyph tiers.
  * [`config.sh`](architecture/shell/config.md) – Persistent configuration management.
* **[Metadata APIs](architecture/api/itunes.md):**
  * [`itunes.md`](architecture/api/itunes.md) – iTunes Search API integration and rate limiting.
  * [`musicbrainz.md`](architecture/api/musicbrainz.md) – MusicBrainz / Cover Art Archive schema normalization.
  * [`lrclib.md`](architecture/api/lrclib.md) – LRCLIB & syncedlyrics integration for timestamped lyrics.
  * [`ytdlp.md`](architecture/api/ytdlp.md) – yt-dlp stream extraction and fallback recovery.
* **[Hardware Constraints](architecture/hardware/rockbox-model.md):**
  * [`rockbox-model.md`](architecture/hardware/rockbox-model.md) – Rockbox database indexing, split album triggers, `ALBUMARTIST` necessity, standalone `cover.jpg` benefits.
  * [`fat32-storage.md`](architecture/hardware/fat32-storage.md) – FAT32 path length limits, illegal characters, and casing normalization.

---

## 3. Python Modules

Comprehensive specifications for each individual engine in `src/modules/` and domain packages:

| Module Document | Source File | Description |
|---|---|---|
| **[`stats.md`](modules/stats.md)** | `src/modules/stats.py` | Analytics, audio formats distribution, and Rockbox health dashboard |
| **[`audit.md`](modules/audit.md)** | `src/modules/audit.py` | Duration auditing against metadata APIs to detect accidental album rips |
| **[`album-expander.md`](modules/album-expander.md)** | `src/modules/album_expander.py` | Unbundling full-album rips into tagged individual tracks |
| **[`covers.md`](modules/covers.md)** | `src/modules/covers.py` | Standalone `cover.jpg` extraction and embedded tag stripping |
| **[`dedup.md`](modules/dedup.md)** | `src/modules/dedup.py` | Deduplication prioritizing lossless quality and relinking playlists |
| **[`fallback.md`](modules/fallback.md)** | `src/modules/fallback.py` | Resilient yt-dlp fallback download and metadata recovery engine |
| **[`genres.md`](modules/genres.md)** | `src/modules/genres.py` | Multi-API genre enrichment via iTunes, Deezer, and MusicBrainz |
| **[`lyrics.md`](modules/lyrics.md)** | `src/modules/lyrics.py` | Multi-threaded timestamped `.lrc` search and tag embedding |
| **[`playlist-repair.md`](modules/playlist-repair.md)**| `src/modules/playlist_repair.py` | Relinking moved/renamed files and pruning dead paths in playlists |
| **[`rockbox-tags.md`](modules/rockbox-tags.md)** | `src/modules/rockbox_tags.py` | Unifying `ALBUM`/`ALBUMARTIST` per folder to prevent split albums |
| **[`organize.md`](modules/organize.md)** | `src/modules/organize.py` | Restructures arbitrary audio trees into canonical Rockbox folder hierarchy |
| **[`search.md`](modules/search.md)** | `src/modules/search.py` | Track and album search via iTunes/MusicBrainz |
| **[`patch.md`](modules/patch.md)** | `src/patch/` | Transcoding and quality upgrade pipeline (`flac`, `mp3`, `opus`) |
| **[`playlists.md`](modules/playlists.md)** | `src/playlists/` | Terminal interactive playlist manager, merger, and deleter |
| **[`romaji.md`](modules/romaji.md)** | `src/romaji/` | Japanese Kanji/Kana transliteration to Hepburn Romaji |
| **[`share.md`](modules/share.md)** | `src/share/` | Reusable utilities (audio metadata, icons, covers, text cleaning) |

---

## 4. Complete CLI Reference

* **[CLI Overview](reference/cli.md):** Grammar rules, global options, and standard exit codes.
* **[Resource Reference](reference/resources/library.md):**
  * [`library.md`](reference/resources/library.md) – `syncdap library <action>`
  * [`artist.md`](reference/resources/artist.md) – `syncdap artist <action>`
  * [`album.md`](reference/resources/album.md) – `syncdap album <action>`
  * [`track.md`](reference/resources/track.md) – `syncdap track <action>`
  * [`playlist.md`](reference/resources/playlist.md) – `syncdap playlist <action>`
  * [`covers.md`](reference/resources/covers.md) – `syncdap covers <action>`
  * [`lyrics.md`](reference/resources/lyrics.md) – `syncdap lyrics <action>`
  * [`tags.md`](reference/resources/tags.md) – `syncdap tags <action>`
  * [`config.md`](reference/resources/config.md) – `syncdap config <action>`
* **[Exit Codes](reference/exit-codes.md):** Detailed guide to exit codes (`0`, `1`, `2`) and Dual-Audience error formatting.
