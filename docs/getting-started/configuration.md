# Configuration & DAP Hardware Mounts

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

## 3. Scrobbler Credentials & Security (`lastfm.conf`)

Last.fm desktop session credentials are saved separately to:
```text
~/.config/syncdap/lastfm.conf
```
- **Permission Invariant:** Automatically set to `0600` (`-rw-------`).
- **Watermark Persistence:** Synchronization timestamps are maintained in `~/.config/syncdap/scrobbler.state`.
- **Log Rotations:** Archived `.scrobbler.log` files are stored in `~/.config/syncdap/logs/`.

---

## 4. DAP Hardware Mount Points

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
