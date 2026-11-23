#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/common.sh
# Purpose: Shared environment, helpers, dependency checks, and formatting
# ==============================================================================

set -uo pipefail

SYNCDAP_VERSION="1.0.0"

# Source iconography and configuration modules
source "$SCRIPT_DIR/src/sh/icons.sh"
source "$SCRIPT_DIR/src/sh/config.sh"

# Global state
export PYTHONPATH="${SCRIPT_DIR}/src:${SCRIPT_DIR}:${PYTHONPATH:-}"
MARKER=""
TEMP_DIR=""
RAW_URL=""
CLEAN_URL=""
AUDIO_FORMAT="mp3"
THREADS=4
SYNCED_ONLY=false
ASSUME_YES=false
KEEP_OLD=false
DRY_RUN=false
VERBOSE=false
QUIET=false
TARGET_ROOT="."
FORCE_ICONS="auto"
YTDLP_JS_ARGS=()

# Load saved configuration defaults
load_config
if [ -n "${CONFIG_THREADS:-}" ]; then THREADS="$CONFIG_THREADS"; fi
if [ -n "${CONFIG_FORMAT:-}" ]; then AUDIO_FORMAT="$CONFIG_FORMAT"; fi
if [ -n "${CONFIG_ROOT_DIR:-}" ]; then TARGET_ROOT="$CONFIG_ROOT_DIR"; fi
if [ "${CONFIG_SYNCED_ONLY:-}" = "true" ]; then SYNCED_ONLY=true; fi

# Initialize terminal symbols & colors
init_iconography

resolve_music_root() {
    local base="${TARGET_ROOT:-.}"
    if [ -d "$base/Music" ]; then
        echo "$base/Music"
    else
        echo "$base"
    fi
}

# Python runner helper with dependencies
run_py() {
    if [ -n "${SYNCDAP_PYTHON:-}" ] && [ -x "$SYNCDAP_PYTHON" ]; then
        "$SYNCDAP_PYTHON" "$@"
    elif command -v uv &>/dev/null; then
        uv run --offline --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 "$@" 2>/dev/null || \
        uv run --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 "$@" 2>/dev/null || \
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
        error_dual "spotDL is not available" "spotdl executable is not installed and uv runtime fallback failed" "" "" "Install spotDL: pip install spotdl or run with uv"
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
    [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ] && return 0
    MARKER=$(mktemp -t syncdap_marker.XXXXXX 2>/dev/null || mktemp /tmp/syncdap_marker.XXXXXX)
    TEMP_DIR=$(mktemp -d -t syncdap_session.XXXXXX 2>/dev/null || mktemp -d /tmp/syncdap_session.XXXXXX)
    trap cleanup EXIT INT TERM
    touch "$MARKER"
}

# Dependency validation
check_dependencies() {
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
        error_dual "Missing required system dependencies" "One or more required binaries were not found in PATH" "${missing_deps[*]}" "" "Install the missing tools via your package manager or installer."
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
            error_dual "Unsupported audio format '$fmt'" "Audio container format is not supported" "$fmt" "" "Supported formats: flac, mp3, m4a, opus, ogg, wav"
            exit 2
            ;;
    esac
}

# Cleanup empty residual directories
cleanup_empty_dirs() {
    find . -mindepth 1 -type d -empty ! -path "./Playlists*" -delete 2>/dev/null || true
}

# Update handler
perform_update() {
    if [ "$QUIET" = false ]; then
        echo -e "${ICON_INFO} Checking for syncdap updates..." >&2
    fi
    if [ -n "${SYNCDAP_PYTHON:-}" ] || (command -v uv &>/dev/null && uv tool list 2>/dev/null | grep -q syncdap); then
        echo -e "${ICON_INFO} Updating rolling release via uv tool..." >&2
        uv tool upgrade syncdap 2>/dev/null || uv tool install --force git+https://github.com/bagi-sh/syncdap.git
        exit 0
    elif [ -f "$SCRIPT_DIR/install.sh" ]; then
        bash "$SCRIPT_DIR/install.sh" --update
    elif [ -d "$SCRIPT_DIR/.git" ]; then
        git -C "$SCRIPT_DIR" pull --rebase
        if command -v uv &>/dev/null; then
            uv run --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 -c "import mutagen, eyed3, requests, pykakasi; print('Dependencies updated')" 2>/dev/null || true
        fi
        echo -e "${GREEN}${ICON_OK} syncdap updated successfully.${RESET}"
    else
        error_dual "Cannot update" "No git repository or install.sh found in $SCRIPT_DIR" "$SCRIPT_DIR" "" "Clone the repository using git or re-run the installer."
        exit 1
    fi
    exit 0
}

# Uninstall handler
perform_uninstall() {
    local yes_flag=""
    [ "$ASSUME_YES" = true ] && yes_flag="-y"
    if [ -f "$SCRIPT_DIR/install.sh" ]; then
        bash "$SCRIPT_DIR/install.sh" --uninstall $yes_flag
        exit 0
    fi

    local target_bin
    target_bin="$(command -v syncdap 2>/dev/null || true)"
    if [ "$ASSUME_YES" != true ]; then
        read -rp "Are you sure you want to uninstall syncdap? [y/N]: " confirm
        case "$confirm" in
            [yY][eE][sS]|[yY]) ;;
            *) echo "Uninstallation aborted."; exit 0 ;;
        esac
    fi

    if [ -n "$target_bin" ] && [ -L "$target_bin" ]; then
        rm -f "$target_bin"
    fi

    if [ -d "$SCRIPT_DIR" ] && [[ "$SCRIPT_DIR" == *"/syncdap"* ]]; then
        rm -rf "$SCRIPT_DIR"
    fi

    echo -e "${GREEN}${ICON_OK} syncdap has been completely uninstalled.${RESET}"
    exit 0
}
