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
| **`library`** | Global maintenance (`status`, `audit`, `dedup`, `optimize`, `patch`, `fix`, `romaji`) | `syncdap library status`<br>`syncdap library optimize -n` |
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

## Documentation Architecture

Exhaustive guides and technical references are organized in the [`docs/`](docs/) directory:

* **[Getting Started](docs/getting-started/installation.md)**
  * [Installation & Dependencies](docs/getting-started/installation.md)
  * [Configuration & DAP Mounts](docs/getting-started/configuration.md)
* **[System Architecture](docs/architecture/overview.md)**
  * [Architectural Overview & Data Flow](docs/architecture/overview.md)
  * [Shell Coordinator Layer](docs/architecture/shell/cli.md)
  * [Metadata API Integration](docs/architecture/api/itunes.md)
  * [Rockbox Hardware Constraints](docs/architecture/hardware/rockbox-model.md)
* **[Python Modules Reference](docs/modules/stats.md)**
  * Per-module documentation for all 15 core engines.
* **[Complete CLI Reference](docs/reference/cli.md)**
  * Exhaustive reference for all resources, actions, flags, and exit codes.

---

## Contributing & License

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

Released under the [GNU General Public License v2](LICENSE).
