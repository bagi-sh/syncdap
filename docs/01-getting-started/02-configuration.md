# Chapter 1.2: Configuration, DAP Mounts & Terminal Environment

> **The Syncdap Book Navigation:** [← Previous Section](01-installation.md) • [Table of Contents](../index.md) • [Next Section →](../02-hardware-target/01-rockbox-model.md)

---

## Pedagogical Context & Prerequisites
In the previous section, we installed `syncdap`. Now, we configure how the tool interacts with your filesystem, resolves target Digital Audio Player (DAP) mount locations, and renders diagnostic terminal output.

---

`syncdap` supports persistent configuration files, runtime environment variables, and CLI flag overrides.

---

## 1. Persistent Configuration (`~/.config/syncdap/config`)

By default, `syncdap` resolves user settings using the standard XDG hierarchy:
1. Custom configuration file passed via `-c <path>` or `--config <path>`.
2. `$XDG_CONFIG_HOME/syncdap/config` (if defined).
3. `~/.config/syncdap/config` (standard user home).
4. `$PWD/.config/syncdap/config` (fallback if user home is read-only).

You can inspect or modify these settings using `syncdap config`:

### Viewing Configuration
```bash
# Display active settings and configuration file path
syncdap config list
```

### Initializing Configuration with All Defaults
Generate a complete, fully-commented configuration file populated with all customizable defaults:
```bash
# Create configuration file if none exists
syncdap config init

# Overwrite existing file with complete defaults
syncdap config init --force
```

### Setting and Getting Values
```bash
# Direct key=value syntax
syncdap config format=flac
syncdap config threads=8
syncdap config cover_name=cover.jpg
syncdap config cover_resolution=600
syncdap config audit_threshold=600

# Alternative 'set' command
syncdap config set icons true

# Retrieve a specific configuration value
syncdap config get root_dir
```

---

## 2. Comprehensive Configuration Key Reference

All settings below can be customized in `~/.config/syncdap/config`:

### Core Runtime & Terminal UX
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `format` | `mp3`, `flac`, `m4a`, `opus`, `ogg`, `wav` | `mp3` | Default audio format for downloads, conversions, and expansions. |
| `threads` | Integer (`1`–`32`) | `4` | Concurrency worker threads for audio scanning, transcoding, and downloads. |
| `root_dir` | Directory path | `.` | Default library path or DAP mount point when `-r` is not passed. |
| `icons` | `auto`, `true`, `false` | `auto` | Terminal iconography: `auto` (detect), `true` (Nerd Font / Unicode), `false` (ASCII). |
| `assume_yes` | `true`, `false` | `false` | Skip interactive confirmation prompts automatically. |

### Cover Artwork & DAP Display
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `cover_name` | Filename (e.g. `cover.jpg`) | `cover.jpg` | Canonical external artwork filename generated for album directories. |
| `cover_resolution`| Integer (`100`–`1400`) | `600` | Download artwork resolution in pixels (e.g. `600` for 600x600, optimal for DAP RAM). |
| `cover_filenames` | Comma-separated names | `cover.jpg,cover.jpeg,cover.png,folder.jpg,folder.jpeg,folder.png` | Recognized front cover filenames during library traversal. |

### Synchronized Lyrics (.lrc)
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `synced_only` | `true`, `false` | `false` | If `true`, reject plain text lyrics and require timestamped `[mm:ss]` files. |

### Rockbox Hardware & Tag Standardization
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `id3_version` | `3`, `4` | `3` | Target ID3v2 version: `3` (ID3v2.3 UTF-16, optimal for Rockbox) or `4` (ID3v2.4). |
| `clean_ghost_files`| `true`, `false` | `true` | Automatically purge OS ghost files (`._*`, `Thumbs.db`, `.DS_Store`) during scans. |
| `ignored_dirs` | Comma-separated | `lost.dir,.trash-1000,.trash,...` | Directories completely excluded from library traversal. |

### Library Audit & Full-Album Rip Detection
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `audit_threshold` | Float / Seconds | `600` | Duration threshold in seconds (600s = 10m) to trigger rip auditing. |
| `audit_ratio` | Float | `1.5` | Ratio multiplier (`local_duration / canonical_duration`) to flag continuous rips. |

### Audioscrobbler & Last.fm Synchronization
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `scrobbler_keep_log`| `true`, `false` | `false` | Retain `.scrobbler.log` on DAP after sync instead of rotating/archiving. |
| `scrobbler_tz_offset`| Integer / Float | *(auto)* | Explicit UTC timezone offset override (e.g. `-3`, `0`). Empty uses host offset. |
| `scrobbler_batch_size`| Integer (`1`–`50`) | `50` | Maximum tracks per Last.fm batch POST request. |

### Media Ingestion & Network APIs
| Key | Valid Options | Default | Description |
|---|---|---|---|
| `spotdl_providers` | Space-separated | `youtube youtube-music soundcloud bandcamp` | Audio stream providers prioritized by spotDL. |
| `spotdl_max_retries`| Integer | `1` | Maximum download retry attempts per track in spotDL. |
| `spotdl_throttled_rate`| Rate string | `100K` | Rate throttling argument passed to yt-dlp to bypass bot challenges. |
| `api_timeout` | Seconds | `8` | Default HTTP request timeout for iTunes, MusicBrainz, and LRCLIB APIs. |

---

## 3. Strict Precedence Hierarchy

Every configuration parameter and preference in `syncdap` resolves through a strict 3-tier precedence hierarchy. Each tier overrides the next, and is overridden by any higher tier:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    Tier 1: CLI Flags (Highest Priority)                 │
│  Explicit arguments passed on the command line (-r, -t, -F, --icons,   │
│  --yes, --synced-only, --tz-offset, --batch-size, --threshold, etc.)    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (overrides when supplied)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Tier 2: Local User Configuration                     │
│  Key-value definitions in active config file (~/.config/syncdap/config, │
│  $XDG_CONFIG_HOME, or custom file passed via -c/--config)               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (overrides when key exists)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 Tier 3: Installation Defaults (Base Tier)               │
│  Built-in defaults hardcoded into syncdap shell and Python runtime      │
│  (threads=4, format=mp3, root_dir=., cover_name=cover.jpg, etc.)       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Precedence Resolution Matrix

| Parameter | Tier 1: CLI Flag | Tier 2: Local Config (`config`) | Tier 3: Installation Default |
|---|---|---|---|
| Target music root | `-r, --root-dir <path>` | `root_dir` or `root-dir` | `.` (current directory) |
| Worker concurrency | `-t, --threads <num>` | `threads` | `4` |
| Audio format | `-F, --format <fmt>` | `format` | `mp3` |
| Iconography tier | `--icons` / `--no-icons` | `icons` | `auto` (auto-detect) |
| Non-interactive prompts | `-y, --yes` | `assume_yes` or `assume-yes` | `false` |
| Synchronized lyrics only | `--synced-only` | `synced_only` or `synced-only`| `false` |
| Retain scrobble log | `--keep-log` | `scrobbler_keep_log` | `false` |
| Explicit timezone offset | `--tz-offset, --timezone`| `scrobbler_tz_offset` | `""` (detected from `#TZ`) |
| Scrobbler batch size | `--batch-size <num>` | `scrobbler_batch_size` | `50` (Last.fm max) |
| Cover filename | `--cover-name <name>` | `cover_name` or `cover-name` | `cover.jpg` |
| Cover resolution | `--cover-resolution <px>`| `cover_resolution` | `600` |
| Audit rip threshold | `-t, --threshold <sec>` | `audit_threshold` | `600.0` (10 minutes) |
| Audit duration ratio | `--ratio <multiplier>` | `audit_ratio` | `1.5` |
| Purge ghost files | `--clean-ghost-files` | `clean_ghost_files` | `true` |
| ID3 standard version | `--id3-version <3\|4>` | `id3_version` | `3` (ID3v2.3 UTF-16) |

### Key Normalization & Compatibility
Configuration keys support both hyphenated (`root-dir`, `synced-only`, `clean-ghost-files`) and underscored (`root_dir`, `synced_only`, `clean_ghost_files`) styles interchangeably. Both forms are normalized during parsing and resolve identically.

### Behavior Examples

#### Example 1: Local Config Overrides Installation Default
Your local configuration contains:
```ini
root_dir=/run/media/bagi/F695-0800/
threads=8
```
Running:
```bash
syncdap library status
```
Result: Targets `/run/media/bagi/F695-0800/` with `8` threads (Tier 2 overrides Tier 3).

#### Example 2: CLI Flag Overrides Local Config
With the same local config as above, running:
```bash
syncdap library status -r /tmp/test_music -t 2
```
Result: Targets `/tmp/test_music` using `2` threads (Tier 1 explicitly overrides Tier 2).

#### Example 3: Custom Configuration File with CLI Override
Running:
```bash
syncdap -c ~/custom_dap.conf -t 16 library optimize
```
Result: Settings from `~/custom_dap.conf` take precedence over standard config, but `-t 16` overrides the thread count from `custom_dap.conf` (Tier 1 > Tier 2 custom > Tier 3).

---

## 4. Scrobbler Credentials & Security (`lastfm.conf`)

Last.fm desktop session credentials are saved separately to:
```text
~/.config/syncdap/lastfm.conf
```
- **Permission Invariant:** Automatically set to `0600` (`-rw-------`).
- **Watermark Persistence:** Synchronization timestamps are maintained in `~/.config/syncdap/scrobbler.state`.
- **Log Rotations:** Archived `.scrobbler.log` files are stored in `~/.config/syncdap/logs/`.

---

## 5. DAP Hardware Mount Points

When connecting an offline Digital Audio Player (DAP) running Rockbox:

1. **Mount your DAP filesystem:**
   ```bash
   sudo mount /dev/sdX1 /mnt/dap
   ```
2. **Execute maintenance directly on the DAP volume:**
   ```bash
   # Sync playback scrobbles
   syncdap scrobbler -r /mnt/dap

   # Complete library optimization
   syncdap library optimize -r /mnt/dap
   ```
3. **Unmount cleanly before disconnecting USB:**
   ```bash
   sync && sudo umount /mnt/dap
   ```
   Ensures FAT32 directory tables and metadata caches are completely flushed.

---

## Summary & Next Steps
With your configuration initialized and mount paths resolved, you are ready to examine the foundational physics that drive every architectural decision in `syncdap`: the Rockbox audio model and hardware storage constraints.

---

> **The Syncdap Book Navigation:** [← Previous Section](01-installation.md) • [Table of Contents](../index.md) • [Next Section →](../02-hardware-target/01-rockbox-model.md)
