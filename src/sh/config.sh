#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/config.sh
# Purpose: Configuration management for syncdap (~/.config/syncdap/config)
# ==============================================================================

if [ -n "${SYNCDAP_CONFIG_FILE:-}" ] && [ -f "$SYNCDAP_CONFIG_FILE" ]; then
    CONFIG_FILE="$SYNCDAP_CONFIG_FILE"
    CONFIG_DIR="$(dirname "$CONFIG_FILE")"
else
    CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/syncdap"
    if ! mkdir -p "$CONFIG_DIR" 2>/dev/null; then
        CONFIG_DIR="$PWD/.config/syncdap"
    fi
    CONFIG_FILE="$CONFIG_DIR/config"
fi

load_config() {
    # Reset config cache to allow clean reloading
    CONFIG_ICONS=""
    CONFIG_THREADS=""
    CONFIG_FORMAT=""
    CONFIG_ROOT_DIR=""
    CONFIG_SYNCED_ONLY=""
    CONFIG_COVER_NAME=""
    CONFIG_COVER_RESOLUTION=""
    CONFIG_COVER_FILENAMES=""
    CONFIG_AUDIT_THRESHOLD=""
    CONFIG_AUDIT_RATIO=""
    CONFIG_CLEAN_GHOST_FILES=""
    CONFIG_KEEP_LOG=""
    CONFIG_TZ_OFFSET=""
    CONFIG_SCROBBLER_BATCH_SIZE=""
    CONFIG_SPOTDL_PROVIDERS=""
    CONFIG_SPOTDL_MAX_RETRIES=""
    CONFIG_SPOTDL_THROTTLED_RATE=""
    CONFIG_API_TIMEOUT=""
    CONFIG_ID3_VERSION=""
    CONFIG_ASSUME_YES=""
    CONFIG_IGNORED_DIRS=""

    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key val || [ -n "$key" ]; do
            # Trim whitespace and normalize hyphen to underscore
            key="$(echo "$key" | tr -d '[:space:]' | tr '-' '_')"
            val="$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            # Ignore comments and empty lines
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

get_config() {
    local target_key="$1"
    local alt_key
    alt_key="$(echo "$target_key" | tr '_' '-')"
    if [ -f "$CONFIG_FILE" ]; then
        grep -E "^(${target_key}|${alt_key})=" "$CONFIG_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2-
    fi
}

set_config() {
    local key="$1"
    local val="$2"
    local norm_key
    norm_key="$(echo "$key" | tr '-' '_')"
    local alt_key
    alt_key="$(echo "$norm_key" | tr '_' '-')"

    mkdir -p "$CONFIG_DIR"
    touch "$CONFIG_FILE"

    if grep -qE "^(${norm_key}|${alt_key})=" "$CONFIG_FILE" 2>/dev/null; then
        sed -i -E "s|^(${norm_key}|${alt_key})=.*|${norm_key}=${val}|" "$CONFIG_FILE"
    else
        echo "${norm_key}=${val}" >> "$CONFIG_FILE"
    fi
}

handle_config_command() {
    local action="${1:-}"

    if [ -z "$action" ] || [ "$action" = "list" ] || [ "$action" = "show" ]; then
        echo "Current configuration (${CONFIG_FILE}):"
        if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
            cat "$CONFIG_FILE"
        else
            echo "  (No configuration set. Defaults in use.)"
        fi
        return 0
    fi

    # Handle key=value syntax (e.g., syncdap config icons=true)
    if [[ "$action" == *"="* ]]; then
        local key="${action%%=*}"
        local val="${action#*=}"
        set_config "$key" "$val"
        echo "✓ Configuration saved: ${key} = ${val}"
        return 0
    fi

    case "$action" in
        set)
            if [ $# -lt 3 ]; then
                echo "✗ Error: 'config set' requires key and value (e.g. syncdap config set icons true)" >&2
                return 2
            fi
            set_config "$2" "$3"
            echo "✓ Configuration saved: $2 = $3"
            ;;
        get)
            if [ $# -lt 2 ]; then
                echo "✗ Error: 'config get' requires a key name" >&2
                return 2
            fi
            local val
            val="$(get_config "$2")"
            if [ -n "$val" ]; then
                echo "$val"
            else
                echo "✗ Key '$2' is not set." >&2
                return 1
            fi
            ;;
        init)
            mkdir -p "$CONFIG_DIR"
            local force_init=false
            if [ "${2:-}" = "-f" ] || [ "${2:-}" = "--force" ] || [ "${FORCE:-false}" = true ]; then
                force_init=true
            fi

            if [ ! -f "$CONFIG_FILE" ] || [ "$force_init" = true ]; then
                cat << 'EOF' > "$CONFIG_FILE"
# ==============================================================================
# syncdap configuration file (~/.config/syncdap/config)
# Modular Rockbox & DAP music library synchronization coordinator
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Core Runtime & Terminal UX
# ------------------------------------------------------------------------------
# Default target audio format: mp3, flac, m4a, opus, ogg, wav
format=mp3

# Worker thread concurrency for audio processing, scanning, and downloads
threads=4

# Default target music library or DAP mount root directory ('.' = current directory)
root_dir=.

# Terminal iconography rendering: 'auto' (detect capability), 'true' (Nerd Font / Unicode), 'false' (ASCII)
icons=auto

# Automatically assume yes on interactive confirmation prompts: 'true' or 'false'
assume_yes=false

# ------------------------------------------------------------------------------
# 2. Cover Artwork & Display
# ------------------------------------------------------------------------------
# Canonical external artwork filename generated for album directories
cover_name=cover.jpg

# Download artwork resolution in pixels (e.g. 600 for 600x600, optimal for DAP RAM)
cover_resolution=600

# Recognized front cover filenames for discovery and inspection (comma-separated)
cover_filenames=cover.jpg,cover.jpeg,cover.png,folder.jpg,folder.jpeg,folder.png

# ------------------------------------------------------------------------------
# 3. Synchronized Lyrics (.lrc)
# ------------------------------------------------------------------------------
# Enforce timestamped lyrics: 'true' (discard plain lyrics), 'false' (allow plain fallback)
synced_only=false

# ------------------------------------------------------------------------------
# 4. Rockbox Hardware & Tag Standardization
# ------------------------------------------------------------------------------
# Target ID3v2 version: '3' (ID3v2.3 UTF-16, optimal for Rockbox) or '4' (ID3v2.4 UTF-8)
id3_version=3

# Automatically purge OS ghost files (._*, Thumbs.db, .DS_Store) during library scans
clean_ghost_files=true

# Directories ignored during audio scanning (comma-separated, case-insensitive)
ignored_dirs=lost.dir,.trash-1000,.trash,system volume information,.android_secure,.rockbox,backup,__pycache__,.git,playlists,lib

# ------------------------------------------------------------------------------
# 5. Library Audit & Full-Album Rip Detection
# ------------------------------------------------------------------------------
# Duration threshold in seconds to trigger duration audit (600s = 10 minutes)
audit_threshold=600

# Multiplier ratio (local_duration / canonical_duration) above which a file is flagged as an album rip
audit_ratio=1.5

# ------------------------------------------------------------------------------
# 6. Audioscrobbler & Last.fm Synchronization
# ------------------------------------------------------------------------------
# Keep .scrobbler.log on DAP after successful synchronization: 'true' or 'false'
scrobbler_keep_log=false

# Explicit timezone UTC offset override (e.g. -3, 0, 2). Leave empty for auto host detection
scrobbler_tz_offset=

# Maximum tracks submitted per Last.fm batch POST request (1 to 50)
scrobbler_batch_size=50

# ------------------------------------------------------------------------------
# 7. Download Ingestion & Stream Extraction
# ------------------------------------------------------------------------------
# Audio providers prioritized by spotDL (space-separated)
spotdl_providers=youtube youtube-music soundcloud bandcamp

# Maximum download retry attempts per track in spotDL
spotdl_max_retries=1

# Rate throttling argument for yt-dlp to bypass bot detection (e.g. '100K')
spotdl_throttled_rate=100K

# Default HTTP request timeout in seconds for metadata APIs (iTunes, MusicBrainz, LRCLIB)
api_timeout=8
EOF
                echo "✓ Initialized configuration with all defaults at: $CONFIG_FILE"
            else
                echo "! Configuration file already exists at: $CONFIG_FILE (use 'syncdap config init --force' to overwrite with all defaults)"
            fi
            ;;
        *)
            # Check if second arg exists for key value syntax
            if [ $# -ge 2 ]; then
                set_config "$1" "$2"
                echo "✓ Configuration saved: $1 = $2"
            else
                echo "✗ Unknown config action: $action" >&2
                echo "Usage: syncdap config [key=value | set <key> <val> | get <key> | list]" >&2
                return 2
            fi
            ;;
    esac
}
