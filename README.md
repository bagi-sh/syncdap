# syncdap

<p align="center">
  <img src="https://www.rockbox.org/rockbox400.png" alt="Rockbox Logo" width="140" />
</p>

<p align="center">
  <strong>Music library management and synchronization tool focused on Rockbox and Digital Audio Players (DAPs).</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPLv2-blue.svg?style=flat-square" alt="License: GPL v2" /></a>
  <img src="https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/bash-4.0+-4EAA25.svg?style=flat-square&logo=gnu-bash&logoColor=white" alt="Bash 4.0+" />
  <img src="https://img.shields.io/badge/platform-Linux-FCC624.svg?style=flat-square&logo=linux&logoColor=black" alt="Platform: Linux" />
  <img src="https://img.shields.io/badge/firmware-Rockbox-0080FF.svg?style=flat-square" alt="Firmware: Rockbox" />
  <img src="https://img.shields.io/badge/powered%20by-uv-DE5FE9.svg?style=flat-square" alt="Astral uv" />
</p>

---

## Overview

`syncdap` automates audio downloading, transcoding, metadata sanitization, and playlist maintenance when syncing streaming libraries to portable hardware players. It is purpose-built to address hardware and firmware constraints common to Rockbox, iPods, and FAT32/exFAT storage volumes.

### Key Capabilities

- **Automated Downloads & Stream Rescue**: Ingest tracks, albums, and playlists via spotDL with automated yt-dlp metadata and stream rescue.
- **In-Place Quality Patching**: Seamlessly switch audio formats (e.g., MP3 to FLAC) while preserving ID3/Vorbis tags, track positions, and playlist integrity.
- **Rockbox & DAP Optimization**: Strip heavy embedded album artwork into lightweight directory-level `cover.jpg` files, unify `ALBUMARTIST` tags to prevent split albums, and sanitize FAT32 path lengths.
- **Japanese Transliteration (Hepburn Romaji)**: Convert Japanese Kanji, Hiragana, and Katakana tags, folder trees, filenames, and `.lrc` synced lyrics to Hepburn Romaji.
- **Playlist Health & Repair**: Relink moved or renamed audio files, prune dead entries, merge playlists, and manage tracks with interactive terminal menus.
- **Fidelity Deduplication**: Detect duplicate tracks across formats and automatically keep the highest audio quality (FLAC > WAV > M4A > OPUS > OGG > MP3).
- **Orchestrated Album Unbundling (`--expand-albums`)**: Detect single-file full-album rips (anomalies where track duration drastically exceeds expected single track length), resolve the official release tracklist, and automatically re-download individual tracks with quality-aware file selection, synced `.lrc` lyrics, Rockbox tag normalization, directory-level cover extraction, and 1-to-N playlist `.m3u8` updates.
- **Duration & Rip Auditor (`--audit-duration`)**: Scan library tracks >= 10 minutes against iTunes and MusicBrainz APIs to detect accidental full-album rips with auto-expansion support.
- **Diagnostics & Metrics**: Generate comprehensive library health reports, format distributions, and storage analytics.

---

## Quick Start

### Installation

Clone the repository and run the standalone installer:

```bash
git clone git@github.com:bagi-sh/syncdap.git
cd syncdap
./install.sh
```

The installer verifies system dependencies (`ffmpeg`, `curl`, `python3`, `uv`), caches required wheels, installs the tool to `~/.local/share/syncdap`, and links the launcher to `~/.local/bin/syncdap`.

> **Note:** Once installed, you can safely delete the cloned repository directory:
> ```bash
> cd .. && rm -rf syncdap
> ```

### Updates

To update `syncdap` to the latest remote release and refresh dependencies:

```bash
syncdap --update
```

*(If you retain the cloned repository, running `./install.sh --update` also fetches latest commits and syncs files).*

### Uninstallation

To cleanly remove `syncdap` and its launchers:

```bash
syncdap --uninstall
```

---

## Usage

```bash
syncdap [COMMAND] [OPTIONS] [TARGET]
```

### Primary Commands

| Command | Arguments | Description |
|---|---|---|
| `<SPOTIFY_URL>` | URL | Download album, playlist, or track from Spotify. |
| `-p`, `--patch` | `[FORMAT] [TARGET]` | Upgrade/patch library tracks or playlist to target format (`flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`). Default: `flac`. |
| `-R`, `--romaji` | `[TARGET]` | Transliterate Japanese tags and paths to Hepburn Romaji. Target can be `--all` or a playlist name. |
| `-P`, `--playlist` | `[NAME]` | Launch interactive playlist manager (create, edit, merge, delete). |
| `-M`, `--merge` | `PL1 PL2 [OUT]` | Merge two playlists and deduplicate shared tracks. |
| `-D`, `--delete` | `PLAYLIST` | Delete a playlist and prompt to purge referenced audio files from disk. |
| `-o`, `--optimize` | None | Run full DAP optimization: deduplicate, strip embedded artwork, sanitize tags, and repair playlists. |
| `-e`, `--embed` | None | Re-embed `cover.jpg` artwork back into audio files. |
| `--dedup` | None | Scan library for duplicates and retain the highest audio quality format. |
| `--fix-tags` | None | Fix inconsistent metadata for Rockbox database indexing (`ALBUMARTIST`, 0-byte tags). |
| `--repair-playlists` | None | Audit playlist files, relinking renamed tracks and pruning dead links. |
| `-g`, `--genres` | None | Enrich genre tags via iTunes, Deezer, and MusicBrainz. |
| `-l`, `--lyrics` | None | Scan and download missing timestamped `.lrc` lyric files. |
| `--embed-lyrics` | None | Scan library and embed lyrics directly into audio metadata. |
| `-s`, `--status` | None | Display terminal dashboard with library statistics and health metrics. |
| `-f`, `--fallback` | `[URL]` | Run yt-dlp fallback recovery directly, or rescue tracks from `erros.spotdl`. |
| `--expand-albums`, `--unbundle` | `[FILE]` | Expand bundled full-album rip(s) into individual tagged tracks via re-download. |
| `--audit-duration` | None | Audit library tracks >= 10m against iTunes/MusicBrainz to detect full-album rips. |
| `--search` | `QUERY` | Search track or album by name without requiring a Spotify URL. |
| `--update` | None | Pull latest remote commits and update syncdap and dependencies. |
| `--uninstall` | None | Completely remove syncdap from the system. |

### Universal Options

| Option | Description |
|---|---|
| `-a`, `--all` | Apply command across entire music library root. |
| `-d`, `--dry-run` | Preview filesystem operations without modifying files on disk. |
| `-y`, `--yes` | Non-interactive mode; automatically confirm prompts. |
| `-F`, `--format <FMT>` | Audio format for downloads or patching (`flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`). |
| `-P`, `--playlist <NAME>`| Target specific playlist (`.m3u8`). |
| `-r`, `--root-dir <DIR>` | Target player or library mount root (e.g. `/run/media/user/DAP` or `.`). |
| `-t`, `--threads <NUM>`  | Number of concurrent worker threads (default: `4`). |
| `--keep-old` | Keep original audio files alongside newly patched files. |
| `--synced-only` | In lyrics operations, only accept timestamped (`[mm:ss]`) LRC files. |
| `-h`, `--help` | Display concise command usage and exit. |

---

## Common Workflows

#### Download an album in FLAC format
```bash
syncdap -F flac "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy"
```

#### Transliterate entire library from Japanese Kanji to Hepburn Romaji
```bash
syncdap -R --all
```

#### Transliterate a specific playlist on a connected DAP in dry-run mode
```bash
syncdap -R -P "CityPop.m3u8" -r /run/media/bagi/DAP -d
```

#### Upgrade tracks in a playlist to FLAC
```bash
syncdap --patch flac "Favorites.m3u8"
```

#### Run full Rockbox optimization (deduplication, artwork stripping, tag fixes)
```bash
syncdap --optimize
```

#### Audit and repair broken playlist references across the library
```bash
syncdap --repair-playlists
```

#### Expand bundled full-album rips into authentic individual tracks
```bash
syncdap --expand-albums
syncdap --expand-albums "/run/media/bagi/DAP/Music/Artist/Album/FullAlbum.mp3"
```

#### Audit library tracks for duration anomalies and accidental full-album rips
```bash
syncdap --audit-duration
```

#### Display library health dashboard
```bash
syncdap --status
```

---

## Project Structure

```text
syncdap/
├── syncdap                 # Main executable CLI coordinator (Bash)
├── install.sh              # Standalone installer, updater, and uninstaller
├── src/
│   ├── modules/            # Standalone media processing modules
│   │   ├── album_expander.py # Orchestrated album unbundling and expansion
│   │   ├── audit.py        # Library duration and full-album rip auditor
│   │   ├── covers.py       # Album artwork extraction and embedding
│   │   ├── dedup.py        # Quality-aware library deduplication
│   │   ├── fallback.py     # Resilient yt-dlp metadata and stream rescue
│   │   ├── genres.py       # Multi-provider genre enrichment
│   │   ├── lyrics.py       # Missing lyric scanner and fetcher
│   │   ├── playlist_repair.py # Playlist auditor and dead link pruner
│   │   ├── rockbox_tags.py # Rockbox database tag normalizer
│   │   ├── search.py       # Search and download by track/album name
│   │   └── stats.py        # Library analytics reporter
│   ├── patch/              # Audio quality patching package
│   │   ├── metadata.py     # Audio tag extraction and transfer
│   │   ├── worker.py       # Download and format validation worker
│   │   ├── playlist.py     # In-playlist track upgrade coordinator
│   │   └── cli.py          # Standalone CLI routing
│   ├── playlists/          # Playlist management package
│   │   ├── core.py         # Playlist search, track resolution, and analysis
│   │   ├── actions.py      # Deletion and merging logic
│   │   ├── manager.py      # Interactive creation and edit workflows
│   │   ├── ui.py           # fzf terminal picker integration
│   │   └── cli.py          # Standalone CLI routing
│   ├── romaji/             # Japanese transliteration package
│   │   ├── translit.py     # Kakasi Hepburn romanization, title casing, FAT32 sanitization
│   │   ├── tags.py         # ID3, Vorbis, and MP4 tag transliteration
│   │   ├── lyrics.py       # Synced .lrc timestamp preservation & transliteration
│   │   ├── playlist.py     # Playlist track relinking and renaming
│   │   ├── engine.py       # Traversal and directory tree renaming engine
│   │   └── cli.py          # Standalone CLI parser
│   ├── sh/                 # Shell modules
│   │   ├── cli.sh          # CLI argument parsing and help output
│   │   ├── common.sh       # Shared environment, dependencies, validation
│   │   ├── downloader.sh   # spotDL orchestration
│   │   ├── orchestrator.sh # Submodule execution dispatchers
│   │   └── playlists.sh    # Post-download playlist path normalization
│   └── share/              # Core shared utilities and constants
│       ├── api.py          # iTunes and MusicBrainz metadata APIs
│       ├── constants.py    # Audio formats, lossless/lossy sets, ignored folders
│       ├── text.py         # Normalization, string sanitization, filename parsing
│       ├── lyrics.py       # Shared LRCLIB and syncedlyrics query provider
│       ├── audio.py        # Mutagen metadata inspection, library walking, quality scoring
│       └── playlists.py    # Common playlist candidate search, path mapping & 1-to-N patching
├── LICENSE                 # GNU General Public License v2.0
├── .gitignore              # Repository ignore definitions
└── README.md
```

---

## License

This project is licensed under the GNU General Public License v2.0. See [LICENSE](LICENSE) for details.
