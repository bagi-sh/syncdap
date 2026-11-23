#!/usr/bin/env bash
# ==============================================================================
# Script: src/sh/main.sh
# Purpose: Modular Rockbox and DAP music library synchronization coordinator
# ==============================================================================

set -uo pipefail

if [ -z "${SCRIPT_DIR:-}" ]; then
    CURRENT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
    if [ -d "$CURRENT_DIR/../../src" ]; then
        SCRIPT_DIR="$(cd "$CURRENT_DIR/../.." && pwd)"
    elif [ -d "$CURRENT_DIR/../sh" ]; then
        SCRIPT_DIR="$(cd "$CURRENT_DIR/.." && pwd)"
    else
        SCRIPT_DIR="$CURRENT_DIR"
    fi
fi

# Locate src/sh directory
if [ -d "$SCRIPT_DIR/src/sh" ]; then
    SH_DIR="$SCRIPT_DIR/src/sh"
elif [ -d "$SCRIPT_DIR/sh" ]; then
    SH_DIR="$SCRIPT_DIR/sh"
else
    echo "Error: syncdap shell modules not found in $SCRIPT_DIR" >&2
    exit 1
fi

# Source modular libraries
source "$SH_DIR/icons.sh"
source "$SH_DIR/config.sh"
source "$SH_DIR/common.sh"
source "$SH_DIR/downloader.sh"
source "$SH_DIR/playlists.sh"
source "$SH_DIR/cli.sh"
source "$SH_DIR/orchestrator.sh"

main() {
    parse_arguments "$@"

    case "$SUBCOMMAND" in
        download)   orchestrate_download ;;
        search)     orchestrate_search ;;
        rescue)     orchestrate_rescue ;;
        status)     orchestrate_status ;;
        dedup)      orchestrate_dedup ;;
        patch)      orchestrate_patch ;;
        optimize)   orchestrate_optimize ;;
        library)    orchestrate_library "$SUBACTION" "${COMMAND_ARGS[@]:-}" ;;
        artist)     orchestrate_artist "$SUBACTION" "${COMMAND_ARGS[@]:-}" ;;
        album)      orchestrate_album "$SUBACTION" "${COMMAND_ARGS[@]:-}" ;;
        track)      orchestrate_track "$SUBACTION" "${COMMAND_ARGS[@]:-}" ;;
        covers)     orchestrate_covers "$SUBACTION" ;;
        lyrics)     orchestrate_lyrics "$SUBACTION" ;;
        playlist)   orchestrate_playlist "$SUBACTION" ;;
        tags)       orchestrate_tags "$SUBACTION" ;;
        scrobbler)  orchestrate_scrobbler "$SUBACTION" ;;
        config)     handle_config_command "${COMMAND_ARGS[@]:-}" ;;
        update)     perform_update ;;
        uninstall)  perform_uninstall ;;
        *)
            error_dual "Unrecognized command '$SUBCOMMAND'" "The specified command is not supported by syncdap" "$SUBCOMMAND" "" "Run 'syncdap --help' for usage instructions."
            exit 2
            ;;
    esac
}

main "$@"
