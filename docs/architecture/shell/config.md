# Shell Coordinator: config.sh

`src/sh/config.sh` manages persistent user configuration stored in standard XDG user configuration directories, injecting defaults into the runtime environment prior to CLI dispatch.

---

## 1. Storage Location & Precedence

The configuration file is resolved according to the following precedence hierarchy:
1. Custom file specified via `-c <path>` or `--config <path>`.
2. `$XDG_CONFIG_HOME/syncdap/config` (if `$XDG_CONFIG_HOME` is set).
3. `~/.config/syncdap/config` (standard user home).
4. `$PWD/.config/syncdap/config` (project-local fallback if user home is read-only).

```bash
# Excerpt from src/sh/config.sh
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/syncdap"
if ! mkdir -p "$CONFIG_DIR" 2>/dev/null; then
    CONFIG_DIR="$PWD/.config/syncdap"
fi
CONFIG_FILE="$CONFIG_DIR/config"
```

---

## 2. Configuration File Grammar & Parser Specification

The file uses a clean `key=value` format. Lines starting with `#` and empty lines are discarded:

```ini
# syncdap configuration
format=mp3
threads=4
root_dir=.
icons=auto
cover_name=cover.jpg
cover_resolution=600
audit_threshold=600
scrobbler_batch_size=50
```

### Parser Implementation (`load_config`)
```bash
# Excerpt from src/sh/config.sh
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key val || [ -n "$key" ]; do
            key="$(echo "$key" | tr -d '[:space:]')"
            val="$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            [[ "$key" =~ ^#.*$ ]] && continue
            [ -z "$key" ] && continue

            case "$key" in
                icons)                  CONFIG_ICONS="$val" ;;
                threads)                CONFIG_THREADS="$val" ;;
                format)                 CONFIG_FORMAT="$val" ;;
                root_dir)               CONFIG_ROOT_DIR="$val" ;;
                synced_only)            CONFIG_SYNCED_ONLY="$val" ;;
                cover_name)             CONFIG_COVER_NAME="$val" ;;
                cover_resolution)       CONFIG_COVER_RESOLUTION="$val" ;;
                cover_filenames)        CONFIG_COVER_FILENAMES="$val" ;;
                audit_threshold)        CONFIG_AUDIT_THRESHOLD="$val" ;;
                audit_ratio)            CONFIG_AUDIT_RATIO="$val" ;;
                clean_ghost_files)      CONFIG_CLEAN_GHOST_FILES="$val" ;;
                scrobbler_keep_log)     CONFIG_KEEP_LOG="$val" ;;
                scrobbler_tz_offset)    CONFIG_TZ_OFFSET="$val" ;;
                scrobbler_batch_size)   CONFIG_SCROBBLER_BATCH_SIZE="$val" ;;
                spotdl_providers)       CONFIG_SPOTDL_PROVIDERS="$val" ;;
                spotdl_max_retries)     CONFIG_SPOTDL_MAX_RETRIES="$val" ;;
                spotdl_throttled_rate)  CONFIG_SPOTDL_THROTTLED_RATE="$val" ;;
                api_timeout)            CONFIG_API_TIMEOUT="$val" ;;
                id3_version)            CONFIG_ID3_VERSION="$val" ;;
                assume_yes)             CONFIG_ASSUME_YES="$val" ;;
                ignored_dirs)           CONFIG_IGNORED_DIRS="$val" ;;
            esac
        done < "$CONFIG_FILE"
    fi
}
```

---

## 3. Supported Configuration Keys

| Key | Valid Values | Runtime Default | Description |
|---|---|---|---|
| `format` | `mp3`, `flac`, `m4a`, `opus`, `ogg`, `wav` | `mp3` | Target audio format for downloads and conversions |
| `threads` | Integer (`1` to `32`) | `4` | Concurrency worker count for downloads and audio scans |
| `root_dir` | Valid directory path | `.` | Default music root or DAP mount point |
| `icons` | `auto`, `true`, `false` | `auto` | Terminal symbol rendering (Nerd Font vs Unicode vs ASCII) |
| `assume_yes` | `true`, `false` | `false` | Bypass interactive confirmation prompts |
| `cover_name` | Filename | `cover.jpg` | Canonical artwork filename written per album |
| `cover_resolution`| Integer (`100`–`1400`) | `600` | Cover artwork download resolution in pixels |
| `cover_filenames` | Comma-separated | `cover.jpg,folder.jpg...` | Recognized cover art names during library scans |
| `synced_only` | `true`, `false` | `false` | Accept only timestamped `[mm:ss]` synchronized lyrics files |
| `id3_version` | `3`, `4` | `3` | ID3v2 standard (3 = ID3v2.3 UTF-16, 4 = ID3v2.4 UTF-8) |
| `clean_ghost_files`| `true`, `false` | `true` | Automatically remove `._*`, `Thumbs.db`, `.DS_Store` |
| `ignored_dirs` | Comma-separated | `lost.dir,.trash...` | Excluded system and playlist directories |
| `audit_threshold` | Seconds | `600` | Duration threshold to audit long tracks (600s = 10m) |
| `audit_ratio` | Float | `1.5` | Ratio multiplier to classify continuous rips |
| `scrobbler_keep_log`| `true`, `false` | `false` | Keep `.scrobbler.log` on DAP after sync |
| `scrobbler_tz_offset`| Integer / Float | *(auto)* | Explicit timezone offset override (e.g. `-3`) |
| `scrobbler_batch_size`| Integer (`1`–`50`) | `50` | Maximum tracks submitted per Last.fm batch |
| `spotdl_providers` | Space-separated | `youtube ...` | Audio stream provider priority for spotDL |
| `spotdl_max_retries`| Integer | `1` | Max download retry attempts in spotDL |
| `spotdl_throttled_rate`| Rate string | `100K` | Rate throttling string passed to yt-dlp |
| `api_timeout` | Seconds | `8` | Default HTTP timeout for metadata APIs |

---

## 4. Invocations

```bash
# View active configuration file and settings
syncdap config list

# Generate full template with all defaults
syncdap config init

# Overwrite existing configuration with all defaults
syncdap config init --force

# Set key=value pairs
syncdap config format=flac
syncdap config cover_name=cover.jpg
syncdap config cover_resolution=600

# Retrieve specific value
syncdap config get format
```
