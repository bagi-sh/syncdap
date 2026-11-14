# syncdap

A command-line music library manager and Spotify synchronization tool designed for Digital Audio Players (DAPs), with dedicated optimizations for Rockbox firmware and FAT32 filesystems.

## Overview

`syncdap` automates the ingestion, audio transcoding, metadata sanitization, and playlist maintenance required when syncing modern streaming libraries to portable hardware players.

Key functional areas:
- **Download & Recovery:** Fetch tracks, albums, and playlists via spotDL with automated yt-dlp fallback recovery.
- **Format Patching:** In-place library audio format switching (e.g. MP3 to FLAC) while preserving tags, track numbers, and playlist links.
- **Rockbox & DAP Optimization:** Strip bloated embedded album artwork into standard directory-level `cover.jpg` files, normalize `ALBUMARTIST` tags to avoid split albums, and sanitize FAT32 file paths.
- **Japanese Transliteration (Romaji):** Convert Kanji, Hiragana, and Katakana tags, folder trees, filenames, and `.lrc` lyrics to Hepburn Romaji.
- **Playlist Maintenance:** Relink renamed tracks, prune dead file references, merge playlists, and manage M3U8 files interactively or headlessly.
- **Deduplication & Diagnostics:** Identify duplicate tracks across formats, score by audio fidelity (FLAC > WAV > M4A > OPUS > OGG > MP3), and report library health statistics.

---

## Requirements

### System Dependencies

Ensure the following tools are installed and accessible in your `PATH`:
- `bash` (4.0+)
- `python3` (3.10+)
- `uv` (recommended for automatic Python dependency resolution)
- `ffmpeg`
- `yt-dlp`
- `spotdl`
- `curl`

Optional:
- `fzf` (enables interactive fuzzy menus for playlist management)
- `nodejs` (provides yt-dlp JavaScript challenge solver)

### Python Dependencies

When `uv` is installed, dependencies are isolated and fetched on-the-fly. If running standard Python directly, install:
```bash
pip install mutagen pykakasi eyed3 requests
```

---

## Installation

Clone the repository and ensure the executable script has execute permissions:

```bash
git clone git@github.com:bagi-sh/syncdap.git
cd syncdap
chmod +x syncdap
```

Optionally, add `syncdap` to your local `PATH`:

```bash
ln -s "$(pwd)/syncdap" ~/.local/bin/syncdap
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
| `-p`, `--patch` | `[FORMAT] [TARGET]` | Upgrade/patch library tracks or playlist to target format (`flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`). Default format: `flac`. |
| `-R`, `--romaji` | `[TARGET]` | Transliterate Japanese Kanji/Kana to Hepburn Romaji and sanitize FAT32 paths. Target can be `--all` or a playlist name. |
| `-P`, `--playlist` | `[NAME]` | Launch interactive playlist manager (create, edit, merge, delete). |
| `-D`, `--delete` | `PLAYLIST` | Remove a playlist and prompt to delete referenced audio files from disk. |
| `-M`, `--merge` | `PL1 PL2 [OUT]` | Merge two playlists, deduplicating shared tracks. |
| `-o`, `--optimize` | None | Run full DAP optimization: deduplicate, strip embedded covers, sanitize tags, and repair playlists. |
| `-e`, `--embed` | None | Revert cover optimization by embedding `cover.jpg` back into audio file tags. |
| `--dedup` | None | Scan library for duplicate tracks and retain the highest audio quality format. |
| `--fix-tags` | None | Fix inconsistent metadata for Rockbox database indexing (`ALBUMARTIST`, remove 0-byte tags). |
| `--repair-playlists` | None | Audit playlist files, relinking renamed tracks and pruning orphaned entries. |
| `-g`, `--genres` | None | Fetch and enrich missing genre tags via iTunes, Deezer, and MusicBrainz. |
| `-l`, `--lyrics` | None | Search and download missing timestamped `.lrc` lyric files. |
| `-s`, `--status` | None | Display terminal dashboard with library statistics, format distribution, and health metrics. |
| `-f`, `--fallback` | `[URL]` | Run yt-dlp fallback recovery directly, or rescue tracks from `erros.spotdl`. |

### Universal Options

| Option | Description |
|---|---|
| `-a`, `--all` | Apply command across entire music library root. |
| `-d`, `--dry-run` | Preview filesystem operations without modifying files on disk. |
| `-y`, `--yes` | Non-interactive mode; automatically confirm prompts. |
| `-F`, `--format <FMT>` | Audio format for downloads or patching (`flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`). |
| `-r`, `--root-dir <DIR>`| Target player or library mount root (e.g. `/run/media/user/DAP` or `.`). |
| `-t`, `--threads <NUM>` | Number of concurrent worker threads (default: `4`). |
| `--keep-old` | Keep original audio files alongside newly patched files. |
| `--synced-only` | In lyrics operations, only accept timestamped (`[mm:ss]`) LRC files. |
| `-h`, `--help` | Display command usage and exit. |

---

## Examples

#### Download an album in FLAC format:
```bash
./syncdap -F flac "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy"
```

#### Transliterate entire library from Japanese Kanji to Hepburn Romaji:
```bash
./syncdap -R --all
```

#### Transliterate a specific playlist on a connected DAP mount in dry-run mode:
```bash
./syncdap -R -P "CityPop.m3u8" -r /run/media/bagi/F695-0800 -d
```

#### Upgrade tracks in a playlist from MP3 to FLAC:
```bash
./syncdap --patch flac "Favorites.m3u8"
```

#### Run full Rockbox optimization (deduplication, artwork stripping, tag fixes):
```bash
./syncdap --optimize
```

#### Audit and repair broken playlist references across the library:
```bash
./syncdap --repair-playlists
```

#### Display library health and analytics:
```bash
./syncdap --status
```

---

## Project Structure

```
syncdap/
├── syncdap                 # Main executable CLI coordinator (Bash)
├── syncdap.sh              # Compatibility symlink
├── lib/
│   ├── sh/                 # Shell modules
│   │   ├── cli.sh          # CLI argument parsing and help output
│   │   ├── common.sh       # Shared environment, dependencies, validation
│   │   ├── downloader.sh   # spotDL orchestration
│   │   ├── orchestrator.sh # Submodule execution dispatchers
│   │   └── playlists.sh    # Post-download playlist path normalization
│   ├── romaji/             # Japanese transliteration package
│   │   ├── translit.py     # Kakasi Hepburn romanization, title casing, FAT32 sanitization
│   │   ├── tags.py         # ID3, Vorbis, and MP4 tag transliteration
│   │   ├── lyrics.py       # Synced .lrc timestamp preservation & transliteration
│   │   ├── playlist.py     # Playlist track relinking and renaming
│   │   ├── engine.py       # Traversal and directory tree renaming engine
│   │   └── cli.py          # Standalone CLI parser
│   ├── playlists/          # Playlist management package
│   │   ├── core.py         # Playlist search, track resolution, and analysis
│   │   ├── actions.py      # Deletion and merging logic
│   │   ├── manager.py      # Interactive creation and edit workflows
│   │   ├── ui.py           # fzf terminal picker integration
│   │   └── cli.py          # Standalone CLI routing
│   ├── patch/              # Audio quality patching package
│   │   ├── metadata.py     # Audio tag extraction and transfer
│   │   ├── worker.py       # Download and format validation worker
│   │   ├── playlist.py     # In-playlist track upgrade coordinator
│   │   └── cli.py          # Standalone CLI routing
│   ├── covers.py           # Album artwork extraction and embedding
│   ├── dedup.py            # Quality-aware library deduplication
│   ├── fallback.py         # Resilient yt-dlp metadata and stream rescue
│   ├── genres.py           # Multi-provider genre enrichment
│   ├── lyrics.py           # Missing lyric scanner and fetcher
│   ├── playlist_ops.py     # Shim importing lib/playlists
│   ├── playlist_repair.py  # Playlist auditor and dead link pruner
│   ├── rockbox_tags.py     # Rockbox database tag normalizer
│   ├── romaji.py           # Shim importing lib/romaji
│   └── stats.py            # Library analytics reporter
├── LICENSE                 # GNU General Public License v2.0
├── .gitignore              # Repository ignore definitions
└── README.md
```

---

## License

This project is licensed under the GNU General Public License v2.0. See [LICENSE](LICENSE) for details.
