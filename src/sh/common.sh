#!/usr/bin/env bash
# ==============================================================================
# Module: src/common.sh
# Purpose: Shared environment, helpers, dependency checks, and formatting
# ==============================================================================

# Exit flags
set -uo pipefail

# ANSI Color codes
BOLD="\033[1m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

# Global state
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
MARKER=""
TEMP_DIR=""
RAW_URL=""
CLEAN_URL=""
AUDIO_FORMAT="mp3"
THREADS=4
SYNCED_ONLY=false
DO_OPTIMIZE=false
OPTIMIZE_ALL=false
EMBED_ALL=false
GENRES_ALL=false
FETCH_LYRICS=false
FALLBACK_ONLY=false
PATCH_MODE=false
PATCH_FORMAT=""
PATCH_FILTER=""
DELETE_PLAYLIST_MODE=false
DELETE_PLAYLIST_TARGET=""
PLAYLIST_MANAGER_MODE=false
PLAYLIST_NAME=""
MERGE_PLAYLIST_MODE=false
MERGE_PL1=""
MERGE_PL2=""
MERGE_OUT=""
ROMAJI_MODE=false
ROMAJI_ROOT="."
ROMAJI_TARGET=""
ALL_MODE=false
ASSUME_YES=false
KEEP_OLD=false
DRY_RUN=false
TARGET_ROOT="."
DEDUP_MODE=false
FIX_TAGS_MODE=false
STATUS_MODE=false
REPAIR_PLAYLISTS_MODE=false
TARGET_M3U=""
YTDLP_JS_ARGS=()
UPDATE_MODE=false
UNINSTALL_MODE=false
SPLIT_MODE=false
SPLIT_FILE=""
CUE_FILE=""
TRACKLIST_FILE=""
AUDIT_DURATION_MODE=false
EMBED_LYRICS_MODE=false
SEARCH_QUERY=""
ALLOW_LIVE=false
ALLOW_REMIX=false

resolve_music_root() {
    local base="${TARGET_ROOT:-.}"
    if [ -d "$base/Music" ]; then
        echo "$base/Music"
    else
        echo "$base"
    fi
}

# Python runner helper with mutagen, eyed3, requests, pykakasi
run_py() {
    if command -v uv &>/dev/null; then
        uv run --offline --with mutagen,eyed3,requests,pykakasi python3 "$@" 2>/dev/null || \
        uv run --with mutagen,eyed3,requests,pykakasi python3 "$@" 2>/dev/null || \
        python3 "$@"
    else
        python3 "$@"
    fi
}

# spotdl runner helper with automatic uv fallback
run_spotdl() {
    if command -v spotdl &>/dev/null; then
        spotdl "$@"
    elif command -v uv &>/dev/null; then
        uv run --with spotdl spotdl "$@"
    else
        echo -e "${RED}❌ Error: spotdl is not installed and uv is unavailable.${RESET}" >&2
        return 1
    fi
}

# Signal handling and temporary resource cleanup
cleanup() {
    local exit_code=$?
    if [ -n "${MARKER:-}" ] && [ -f "$MARKER" ]; then
        rm -f "$MARKER" 2>/dev/null || true
    fi
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR" 2>/dev/null || true
    fi
    exit "$exit_code"
}

# Environment setup
setup_environment() {
    MARKER=$(mktemp -t spotdl_marker.XXXXXX 2>/dev/null || mktemp)
    TEMP_DIR=$(mktemp -d -t spotdl_session.XXXXXX 2>/dev/null || mktemp -d)
    trap cleanup EXIT INT TERM
    touch "$MARKER"
}

# Dependency validation
check_dependencies() {
    echo -e "${CYAN}🔍 Checking system dependencies...${RESET}"
    local required_deps=(yt-dlp ffmpeg python3 uv grep curl)
    local missing_deps=()

    for cmd in "${required_deps[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    if ! command -v spotdl &>/dev/null && ! command -v uv &>/dev/null; then
        missing_deps+=("spotdl")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}❌ Error: Missing required tools:${RESET}"
        for dep in "${missing_deps[@]}"; do
            echo "   - $dep"
        done
        exit 1
    fi

    # Optional JavaScript runtime support for yt-dlp
    if command -v node &>/dev/null; then
        YTDLP_JS_ARGS=(--js-runtimes "node:$(command -v node)")
    fi
}

# Validate audio format and return spotdl/yt-dlp arguments
validate_format() {
    local fmt="${1:-mp3}"
    fmt=$(echo "$fmt" | tr '[:upper:]' '[:lower:]')

    case "$fmt" in
        flac)
            SPOTDL_FORMAT_ARGS=(--format flac --bitrate auto)
            YTDLP_FORMAT_ARGS=(-x --audio-format flac --audio-quality 0)
            AUDIO_EXT="flac"
            ;;
        mp3)
            SPOTDL_FORMAT_ARGS=(--format mp3 --bitrate 320k)
            YTDLP_FORMAT_ARGS=(-x --audio-format mp3 --audio-quality 0)
            AUDIO_EXT="mp3"
            ;;
        m4a)
            SPOTDL_FORMAT_ARGS=(--format m4a --bitrate 320k)
            YTDLP_FORMAT_ARGS=(-x --audio-format m4a --audio-quality 0)
            AUDIO_EXT="m4a"
            ;;
        opus)
            SPOTDL_FORMAT_ARGS=(--format opus --bitrate auto)
            YTDLP_FORMAT_ARGS=(-x --audio-format opus --audio-quality 0)
            AUDIO_EXT="opus"
            ;;
        ogg)
            SPOTDL_FORMAT_ARGS=(--format ogg --bitrate 320k)
            YTDLP_FORMAT_ARGS=(-x --audio-format vorbis --audio-quality 0)
            AUDIO_EXT="ogg"
            ;;
        wav)
            SPOTDL_FORMAT_ARGS=(--format wav --bitrate auto)
            YTDLP_FORMAT_ARGS=(-x --audio-format wav)
            AUDIO_EXT="wav"
            ;;
        *)
            echo -e "${RED}❌ Error: Unsupported audio format '$fmt'.${RESET}"
            echo "Supported formats: flac, mp3, m4a, opus, ogg, wav"
            exit 1
            ;;
    esac
}

# Cleanup empty residual directories
cleanup_empty_dirs() {
    find . -mindepth 1 -type d -empty ! -path "./Playlists*" -delete 2>/dev/null || true
}

# --- UPDATE & UNINSTALL HANDLERS ---
perform_update() {
    echo -e "${BOLD}${BLUE}🔄 Checking for syncdap updates...${RESET}"
    if [ -f "$SCRIPT_DIR/install.sh" ]; then
        bash "$SCRIPT_DIR/install.sh" --update
    elif [ -d "$SCRIPT_DIR/.git" ]; then
        echo -e "${CYAN}📥 Pulling latest commits from git repository...${RESET}"
        git -C "$SCRIPT_DIR" pull --rebase
        if command -v uv &>/dev/null; then
            echo -e "${CYAN}⚡ Refreshing Python dependencies cache...${RESET}"
            uv run --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 -c "import mutagen, eyed3, requests, pykakasi; print('✅ Dependencies updated')" 2>/dev/null || true
        fi
        echo -e "${GREEN}✅ syncdap updated successfully!${RESET}"
    else
        echo -e "${RED}❌ Error: Cannot update. No git repository or install.sh found in $SCRIPT_DIR.${RESET}"
        exit 1
    fi
    exit 0
}

perform_uninstall() {
    echo -e "${BOLD}${YELLOW}⚠️  Uninstall syncdap${RESET}"
    local yes_flag=""
    [ "$ASSUME_YES" = true ] && yes_flag="-y"
    if [ -f "$SCRIPT_DIR/install.sh" ]; then
        bash "$SCRIPT_DIR/install.sh" --uninstall $yes_flag
        exit 0
    fi

    local target_bin
    target_bin="$(command -v syncdap 2>/dev/null || true)"
    echo -e "${YELLOW}This will remove syncdap from your system.${RESET}"
    if [ "$ASSUME_YES" != true ]; then
        read -rp "Are you sure you want to uninstall syncdap? [y/N]: " confirm
        case "$confirm" in
            [yY][eE][sS]|[yY]) ;;
            *) echo "Uninstallation aborted."; exit 0 ;;
        esac
    fi

    if [ -n "$target_bin" ] && [ -L "$target_bin" ]; then
        echo "Removing launcher: $target_bin"
        rm -f "$target_bin"
    fi

    if [ -d "$SCRIPT_DIR" ] && [[ "$SCRIPT_DIR" == *"/syncdap"* ]]; then
        echo "Removing installation files: $SCRIPT_DIR"
        rm -rf "$SCRIPT_DIR"
    fi

    echo -e "${GREEN}✅ syncdap has been completely uninstalled.${RESET}"
    exit 0
}
