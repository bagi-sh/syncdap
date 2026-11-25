# syncdap

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Bash 4.0+](https://img.shields.io/badge/bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://kernel.org)

Modular synchronization, metadata standardization, and media maintenance coordinator optimized for **Rockbox firmware** and audiophile Digital Audio Players (DAPs).

---

## Installation

### Option 1: Via `uv tool` (Recommended)
Install `syncdap` into an isolated Python environment and link it to `~/.local/bin/syncdap`:
```bash
uv tool install git+https://github.com/bagi-sh/syncdap.git
```
To update to the latest bleeding-edge commit at any time:
```bash
syncdap update
# or: uv tool upgrade syncdap
```

### Option 2: Standalone Lean Installer (Linux, macOS, WSL)
Installs only the lightweight runtime (<1 MB) without repository history or documentation bloat:
```bash
curl -fsSL https://raw.githubusercontent.com/bagi-sh/syncdap/main/install.sh | bash
```
Or from a local clone:
```bash
git clone https://github.com/bagi-sh/syncdap.git
cd syncdap
./install.sh
```

---

## Quickstart

### Prerequisites
* Linux environment with **Bash 4.0+** and **Python 3.10+**
* `ffmpeg`, `yt-dlp`, `curl`, and `uv` (or `python3-pip`)

### 30-Second Ingestion & Sync
```bash
# 1. Clone repository
git clone https://github.com/bagi-sh/syncdap.git
cd syncdap

# 2. Inspect music library status
./syncdap library status

# 3. Ingest album or playlist from Spotify URL directly into your DAP mount
./syncdap download "https://open.spotify.com/album/..." -r /mnt/dap

# 4. Run complete Rockbox library optimization (covers + tags + dedup)
./syncdap library optimize -r /mnt/dap
```

---

## Entity-First CLI Grammar

Commands follow a strict, predictable hierarchy: `syncdap <resource> <action> [target] [options]`.

| Resource | Scope / Actions | Example Invocations |
|---|---|---|
| **`library`** | Global maintenance (`status`, `audit`, `dedup`, `optimize`, `patch`, `fix`, `organize`, `romaji`) | `syncdap library status`<br>`syncdap library organize -n` |
| **`artist`** | Artist directory actions (`status`, `audit`, `dedup`, `fix`, `romaji`, `patch`) | `syncdap artist status "Queen"`<br>`syncdap artist fix "Radiohead"` |
| **`album`** | Album folder actions (`status`, `audit`, `dedup`, `expand`, `optimize`, `patch`, `fix`, `romaji`) | `syncdap album audit ./Abbey_Road/`<br>`syncdap album expand ./Rip.mp3` |
| **`track`** | Single-file actions (`status`, `audit`, `expand`, `patch`, `romaji`) | `syncdap track status ./song.flac`<br>`syncdap track patch mp3 ./song.wav` |
| **`playlist`**| M3U/M3U8 playlist tools (`manage`, `merge`, `delete`, `repair`) | `syncdap playlist manage`<br>`syncdap playlist repair` |
| **`covers`**  | Artwork management (`optimize`, `embed`) | `syncdap covers optimize`<br>`syncdap covers embed` |
| **`lyrics`**  | Synchronized `.lrc` maintenance (`fetch`, `embed`) | `syncdap lyrics fetch --synced-only` |
| **`tags`**    | Metadata normalization (`fix`, `genres`, `romaji`) | `syncdap tags fix`<br>`syncdap tags genres` |
| **`scrobbler`**| Rockbox `.scrobbler.log` sync & Last.fm management | `syncdap scrobbler status`<br>`syncdap scrobbler -r /mnt/dap` |
| **`config`**  | Persistent settings inspection and updates | `syncdap config icons=true`<br>`syncdap config list` |

---

## Standard Global Flags

| Flag | Short | Description |
|---|---|---|
| `--help` | `-h` | Display concise usage, resources, or per-resource action help |
| `--version` | `-V` | Output version string (`syncdap 1.0.0`) and exit |
| `--dry-run` | `-n` | Simulate execution without modifying audio files or tags |
| `--root-dir <path>` | `-r` | Target music directory or DAP mount root (default: `.`) |
| `--threads <num>` | `-t` | Worker thread concurrency for downloads and audio scans (default: `4`) |
| `--format <fmt>` | `-F` | Target audio format: `flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav` |
| `--json` | | Output structured machine-readable JSON data |
| `--plain` | | Output headerless, tab-separated plain text for Unix pipelines |
| `--icons` / `--no-icons` | | Force enable or disable monochromatic Nerd Font symbols |

---

## The Syncdap Book (Documentation)

Exhaustive guides, architecture specifications, and operational manuals are organized as an 8-chapter book in the [`docs/`](docs/) directory:

* **[The Syncdap Book Overview](docs/index.md)** – Master reading guide, curriculum arc, and syllabus.
* **[Chapter 1: Getting Started](docs/01-getting-started/01-installation.md)**
  * [1.1 Installation & Toolchain Prerequisites](docs/01-getting-started/01-installation.md)
  * [1.2 Configuration & DAP Mount Points](docs/01-getting-started/02-configuration.md)
* **[Chapter 2: The Hardware & Target Environment](docs/02-hardware-target/01-rockbox-model.md)**
  * [2.1 The Rockbox Audio & Database Model](docs/02-hardware-target/01-rockbox-model.md)
  * [2.2 FAT32 Storage Constraints & VFS Limits](docs/02-hardware-target/02-fat32-storage.md)
* **[Chapter 3: Two-Tier Architecture & Execution Runtime](docs/03-architecture-and-runtime/01-two-tier-model.md)**
  * [3.1 Two-Tier Execution Model & Boundaries](docs/03-architecture-and-runtime/01-two-tier-model.md)
  * [3.2 POSIX CLI Grammar & Routing](docs/03-architecture-and-runtime/02-shell-cli.md)
  * [3.3 Workflow Orchestration Pipelines](docs/03-architecture-and-runtime/03-shell-orchestrator.md)
  * [3.4 Runtime Lifecycle & Signal Trapping](docs/03-architecture-and-runtime/04-shell-lifecycle.md)
* **[Chapter 4: Ingestion Pipeline & Metadata APIs](docs/04-ingestion-and-apis/01-ytdlp.md)**
  * [4.1 yt-dlp Audio Stream Extraction](docs/04-ingestion-and-apis/01-ytdlp.md)
  * [4.2 iTunes Search API Integration](docs/04-ingestion-and-apis/02-itunes.md)
  * [4.3 MusicBrainz & Cover Art Archive](docs/04-ingestion-and-apis/03-musicbrainz.md)
  * [4.4 LRCLIB Synchronized Lyrics](docs/04-ingestion-and-apis/04-lrclib.md)
  * [4.5 Last.fm Web Auth & Scrobbler Protocol](docs/04-ingestion-and-apis/05-lastfm.md)
* **[Chapter 5: Audio Normalization & Library Engines](docs/05-core-engines/01-organize.md)**
  * [5.1 Canonical Folder Organization](docs/05-core-engines/01-organize.md)
  * [5.2 Rockbox Tag Normalization & Split Album Prevention](docs/05-core-engines/02-rockbox-tags.md)
  * [5.3 Artwork Optimization & APIC Stripping](docs/05-core-engines/03-covers.md)
  * [5.4 Duration Auditing & Rip Detection](docs/05-core-engines/04-audit.md)
  * [5.5 Full-Album Rip Expansion](docs/05-core-engines/05-album-expander.md)
  * [5.6 Audio Transcoding & Patching](docs/05-core-engines/06-patch.md)
  * [5.7 Lossless Deduplication](docs/05-core-engines/07-dedup.md)
  * [5.8 Fallback Stream Rescue](docs/05-core-engines/08-fallback.md)
  * [5.9 Multi-Provider Genre Enrichment](docs/05-core-engines/09-genres.md)
  * [5.10 Interactive Search](docs/05-core-engines/10-search.md)
  * [5.11 Concurrent Lyrics Download](docs/05-core-engines/11-lyrics.md)
  * [5.12 Library Health Analytics](docs/05-core-engines/12-stats.md)
* **[Chapter 6: Specialized Domain Subsystems](docs/06-specialized-subsystems/01-playlists.md)**
  * [6.1 Interactive Terminal Playlists](docs/06-specialized-subsystems/01-playlists.md)
  * [6.2 Fuzzy Levenshtein Playlist Relinking](docs/06-specialized-subsystems/02-playlist-repair.md)
  * [6.3 Japanese Romaji Transliteration Pipeline](docs/06-specialized-subsystems/03-romaji.md)
  * [6.4 Rockbox Scrobbler Synchronization](docs/06-specialized-subsystems/04-scrobbler.md)
* **[Chapter 7: Shared Architecture & Core Foundations](docs/07-shared-utilities/01-architecture.md)**
  * [7.1 Shared Package Architecture](docs/07-shared-utilities/01-architecture.md)
  * [7.2 Universal Audio Metadata Engine](docs/07-shared-utilities/02-audio-engine.md)
  * [7.3 String Normalization & FAT32 Sanitization](docs/07-shared-utilities/03-text-sanitization.md)
  * [7.4 Constants, HTTP Pooling & Terminal Presentation](docs/07-shared-utilities/04-constants-and-runtime.md)
* **[Chapter 8: Command-Line Interface Reference](docs/08-cli-reference/01-grammar.md)**
  * [8.1 CLI Grammar & Global Options](docs/08-cli-reference/01-grammar.md)
  * [8.2 Exit Codes & Dual-Audience Diagnostics](docs/08-cli-reference/02-exit-codes.md)
  * [8.3 Complete Per-Resource Manual](docs/08-cli-reference/resources/01-library.md)

---

## Contributing & License

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

Released under the [GNU General Public License v2](LICENSE).
