# The Syncdap Book

Welcome to **The Syncdap Book**, the comprehensive architectural guide, engineering manual, and operational reference for `syncdap` — the modular media coordinator, tag normalizer, and audio maintenance engine designed for **Rockbox firmware** and audiophile Digital Audio Players (DAPs).

---

## How to Read This Book

This book is organized into **8 sequential chapters** structured specifically to build deep technical comprehension from first principles:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Getting Started: Installation, prerequisites, configuration, mount points│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. The Target Environment: Rockbox audio model, 32MB RAM limits, FAT32 VFS │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Architecture & Runtime: Two-tier POSIX Shell + Python execution model    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Ingestion & External APIs: yt-dlp, spotDL, iTunes, MusicBrainz, Last.fm  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. Core Audio Engines: Canonical organization, split-album tags, covers     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. Specialized Subsystems: Playlists, fuzzy relinking, Romaji, scrobbling   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. Shared Infrastructure: Universal audio engine, text sanitizer, constants │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. CLI & Resource Reference: Full grammar, options, exit codes, and manuals │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Table of Contents

### [Chapter 1: Getting Started](01-getting-started/01-installation.md)
* **[1.1 Installation, Toolchains & Dependencies](01-getting-started/01-installation.md)** – System dependencies (`uv`, `ffmpeg`, `yt-dlp`), local builds, and upgrades.
* **[1.2 Configuration, DAP Mounts & Terminal Environment](01-getting-started/02-configuration.md)** – Persistent configuration (`~/.config/syncdap/config`), mount point resolution, and Nerd Font symbols.

### [Chapter 2: The Hardware & Target Environment](02-hardware-target/01-rockbox-model.md)
* **[2.1 The Rockbox Audio & Database Model](02-hardware-target/01-rockbox-model.md)** – 32MB RAM constraints, `database.db` indexing, split-album triggers, `ALBUMARTIST` invariants, and ID3v2.3 UTF-16 BOM requirements.
* **[2.2 FAT32 Storage Constraints & VFS Limits](02-hardware-target/02-fat32-storage.md)** – 255-byte path limits, illegal character sets, trailing dot/space VFS corruption, and write amplification.

### [Chapter 3: Two-Tier Architecture & Execution Runtime](03-architecture-and-runtime/01-two-tier-model.md)
* **[3.1 Two-Tier Execution Model & Architecture Boundaries](03-architecture-and-runtime/01-two-tier-model.md)** – Process boundaries between POSIX Bash coordinators and Python processing engines.
* **[3.2 CLI Grammar Parser & Option Routing (`cli.sh`)](03-architecture-and-runtime/02-shell-cli.md)** – Entity-first grammar validation and option routing.
* **[3.3 Execution Coordinator & Workflow Pipelines (`orchestrator.sh`)](03-architecture-and-runtime/03-shell-orchestrator.md)** – Pipeline orchestration across library, artist, album, and track resources.
* **[3.4 Runtime Lifecycle, Signal Traps & Temp Directories (`common.sh`)](03-architecture-and-runtime/04-shell-lifecycle.md)** – Signal traps (`trap cleanup`), temporary directory lifecycles, and runner wrappers.
* **[3.5 External Ingestion Wrapper & Recovery Traps (`downloader.sh`)](03-architecture-and-runtime/05-shell-downloader.md)** – spotDL execution, bitrate error capture, and fallback recovery triggers.
* **[3.6 Shell Playlist Synchronization & VFS Remapping (`playlists.sh`)](03-architecture-and-runtime/06-shell-playlists.md)** – Syncing local playlists to DAP storage with relative path normalization.
* **[3.7 Terminal Capabilities & Monochromatic Glyphs (`icons.sh`)](03-architecture-and-runtime/07-shell-icons.md)** – Monochromatic glyph tiers and terminal capability detection.
* **[3.8 Shell Configuration Management (`config.sh`)](03-architecture-and-runtime/08-shell-config.md)** – Shell-based configuration reader and setter.

### [Chapter 4: Ingestion Pipeline & Metadata APIs](04-ingestion-and-apis/01-ytdlp.md)
* **[4.1 Audio Stream Extraction & yt-dlp Integration](04-ingestion-and-apis/01-ytdlp.md)** – Audio stream extraction, post-processing flags, and audio extraction pipelines.
* **[4.2 iTunes Search API: Commercial Metadata & 600x600 Artwork](04-ingestion-and-apis/02-itunes.md)** – Query parameters, genre mapping, and artwork URL transformation.
* **[4.3 MusicBrainz & Cover Art Archive: The Open Database](04-ingestion-and-apis/03-musicbrainz.md)** – Rate limits, User-Agent enforcement, and schema navigation.
* **[4.4 LRCLIB & Syncedlyrics: Synchronized Lyrics (.lrc)](04-ingestion-and-apis/04-lrclib.md)** – REST endpoints, timestamp formatting, and fallback retrieval.
* **[4.5 Last.fm Web Authentication & Scrobbler Protocol](04-ingestion-and-apis/05-lastfm.md)** – Desktop web auth handshake, 3-second polling, MD5 signatures, and batch submission contracts.

### [Chapter 5: Audio Normalization & Library Engines](05-core-engines/01-organize.md)
* **[5.1 Canonical Library Organization (`organize.py`)](05-core-engines/01-organize.md)** – Restructuring arbitrary folders into `{AlbumArtist}/{Album}/`, sidecar migration (`.lrc`, `cover.jpg`), and 2-phase move planning.
* **[5.2 Tag Normalization & Split Album Prevention (`rockbox_tags.py`)](05-core-engines/02-rockbox-tags.md)** – Majority voting for album artists and ID3v2.3 tag enforcement.
* **[5.3 Artwork Optimization & APIC Stripping (`covers.py`)](05-core-engines/03-covers.md)** – Extracting external `cover.jpg` and stripping bulky embedded APIC frames to save DAP RAM.
* **[5.4 Duration Auditing & Rip Detection (`audit.py`)](05-core-engines/04-audit.md)** – Detecting accidental full-album single-file rips (>600s).
* **[5.5 Full-Album Rip Expansion & Splitting (`album_expander.py`)](05-core-engines/05-album-expander.md)** – Unbundling single-file rips into individual tagged tracks via CUE/API duration matching.
* **[5.6 Transcoding & Quality Upgrade Pipeline (`patch/`)](05-core-engines/06-patch.md)** – Multithreaded ffmpeg conversion, tag preservation, and playlist updates.
* **[5.7 Lossless-Prioritizing Deduplication (`dedup.py`)](05-core-engines/07-dedup.md)** – Purging lossy duplicates (FLAC > Opus > MP3) and relinking playlist references.
* **[5.8 Fallback Recovery & Stream Rescue (`fallback.py`)](05-core-engines/08-fallback.md)** – Resilient multi-candidate stream search and rescue.
* **[5.9 Multi-Provider Genre Enrichment (`genres.py`)](05-core-engines/09-genres.md)** – Heuristic genre resolution across iTunes, Deezer, and MusicBrainz.
* **[5.10 Interactive Metadata Search Engine (`search.py`)](05-core-engines/10-search.md)** – Interactive terminal metadata resolution.
* **[5.11 Concurrent Synchronized Lyrics Engine (`lyrics.py`)](05-core-engines/11-lyrics.md)** – Multithreaded `.lrc` download and tag embedding.
* **[5.12 Library Analytics & Rockbox Health Dashboard (`stats.py`)](05-core-engines/12-stats.md)** – Bitrate histograms, codec distributions, and Rockbox compliance reporting.

### [Chapter 6: Specialized Domain Subsystems](06-specialized-subsystems/01-playlists.md)
* **[6.1 Interactive Playlist Management (`src/playlists/`)](06-specialized-subsystems/01-playlists.md)** – Curses-like terminal playlist manager, merging, and pruning.
* **[6.2 Fuzzy Levenshtein Playlist Relinking (`playlist_repair.py`)](06-specialized-subsystems/02-playlist-repair.md)** – Re-attaching broken playlist entries after reorganization.
* **[6.3 Japanese Romaji Transliteration Pipeline (`src/romaji/`)](06-specialized-subsystems/03-romaji.md)** – Transliterating Kanji/Kana in tags, lyrics, playlists, and filenames to Hepburn Romaji.
* **[6.4 Rockbox Scrobbler Synchronization (`src/scrobbler/`)](06-specialized-subsystems/04-scrobbler.md)** – `.scrobbler.log` parsing, `#TZ/UNKNOWN` firmware handling, deduplication state ledger, and Last.fm sync.

### [Chapter 7: Shared Architecture & Core Foundations](07-shared-utilities/01-architecture.md)
* **[7.1 Shared Architecture & Package Boundaries (`src/share/`)](07-shared-utilities/01-architecture.md)** – Responsibilities and boundaries of the foundational support package.
* **[7.2 Universal Audio Metadata Abstraction (`audio.py`)](07-shared-utilities/02-audio-engine.md)** – Universal Mutagen abstraction, tag matrices, and ID3v2.3 UTF-16 BOM writing.
* **[7.3 String Normalization & FAT32 Sanitization (`text.py`)](07-shared-utilities/03-text-sanitization.md)** – Path sanitization, VFS illegal character stripping, and fuzzy matching tokens.
* **[7.4 System Constants, HTTP Pooling & Terminal Presentation](07-shared-utilities/04-constants-and-runtime.md)** – Thresholds, connection pooling, and Nerd Font glyphs.

### [Chapter 8: Command-Line Interface Reference](08-cli-reference/01-grammar.md)
* **[8.1 Entity-First CLI Grammar & Global Options](08-cli-reference/01-grammar.md)** – Grammar syntax, option matrix, stdin/stdout piping contracts.
* **[8.2 Exit Codes & Dual-Audience Diagnostic Formatting](08-cli-reference/02-exit-codes.md)** – Standard exit codes (`0`, `1`, `2`) and machine/human stream separation.
* **8.3 Complete Resource Reference Manual:**
  * **[8.3.1 `syncdap library`](08-cli-reference/resources/01-library.md)** – Global operations (`status`, `audit`, `dedup`, `optimize`, `patch`, `fix`, `organize`, `romaji`).
  * **[8.3.2 `syncdap artist`](08-cli-reference/resources/02-artist.md)** – Artist-scoped operations.
  * **[8.3.3 `syncdap album`](08-cli-reference/resources/03-album.md)** – Album-scoped operations.
  * **[8.3.4 `syncdap track`](08-cli-reference/resources/04-track.md)** – Single-track operations.
  * **[8.3.5 `syncdap playlist`](08-cli-reference/resources/05-playlist.md)** – Playlist management and repair.
  * **[8.3.6 `syncdap covers`](08-cli-reference/resources/06-covers.md)** – Artwork extraction and embedding.
  * **[8.3.7 `syncdap lyrics`](08-cli-reference/resources/07-lyrics.md)** – Synchronized `.lrc` maintenance.
  * **[8.3.8 `syncdap tags`](08-cli-reference/resources/08-tags.md)** – Tag standardization and genre enrichment.
  * **[8.3.9 `syncdap scrobbler`](08-cli-reference/resources/09-scrobbler.md)** – Offline `.scrobbler.log` sync.
  * **[8.3.10 `syncdap config`](08-cli-reference/resources/10-config.md)** – Persistent configuration inspection and modification.
