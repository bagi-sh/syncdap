#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/orchestrator.sh
# Purpose: Execution coordinator for media processing submodules
# ==============================================================================

# --- DOWNLOAD ORCHESTRATION ---
orchestrate_download() {
    local target_url="${RAW_URL:-${COMMAND_ARGS[0]:-}}"
    if [ -z "$target_url" ]; then
        error_dual "Missing download target" "A Spotify URL is required for download" "syncdap download <URL>" "" "Example: syncdap download 'https://open.spotify.com/album/...'"
        exit 2
    fi

    check_dependencies
    setup_environment

    validate_url "$target_url"
    process_download
}

# --- SEARCH ORCHESTRATION ---
orchestrate_search() {
    local query="${COMMAND_ARGS[*]:-}"
    if [ -z "$query" ]; then
        error_dual "Missing search query" "A track or album name query is required" "syncdap search <query>" "" "Example: syncdap search 'The Beatles Abbey Road'"
        exit 2
    fi

    setup_environment

    if [ "$QUIET" = false ]; then
        echo -e "${ICON_FIND} Resolving music metadata for: ${BOLD}'$query'${RESET}" >&2
    fi

    local meta_json
    meta_json="$(run_py "$SCRIPT_DIR/src/modules/search.py" "$query" --json 2>/dev/null)"

    if [ -z "$meta_json" ] || [ "$meta_json" = "null" ]; then
        error_dual "Metadata resolution failed" "No matching tracks or albums found on iTunes/MusicBrainz" "$query" "" "Try a more specific search query: syncdap search '<artist> <title>'"
        exit 1
    fi

    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo "$meta_json"
        return 0
    fi

    local meta_file="$TEMP_DIR/search_resolved.json"
    echo "$meta_json" > "$meta_file"

    if [ "$QUIET" = false ]; then
        echo -e "${ICON_DL} Downloading resolved track..." >&2
    fi

    run_py "$SCRIPT_DIR/src/modules/fallback.py" \
        "$meta_file" \
        "$TEMP_DIR" \
        "" \
        "$THREADS" \
        "$SYNCED_ONLY" \
        "$AUDIO_FORMAT" \
        "${YTDLP_JS_ARGS[*]:-}"
}

# --- RESCUE ORCHESTRATION ---
orchestrate_rescue() {
    setup_environment
    local target="${COMMAND_ARGS[0]:-}"
    local batch_meta="$TEMP_DIR/batch_meta.spotdl"
    local has_targets=false

    if [ -n "$target" ] && [[ "$target" =~ ^https://open\.spotify\.com/ ]]; then
        if [ "$QUIET" = false ]; then
            echo -e "${ICON_DL} Fetching stream metadata for rescue target..." >&2
        fi
        run_spotdl save "$target" --save-file "$batch_meta" >/dev/null 2>&1 || true
        [ -s "$batch_meta" ] && has_targets=true
    elif [ -s "erros.spotdl" ]; then
        mapfile -t failed_urls < <(grep -oE 'https://open\.spotify\.com/track/[a-zA-Z0-9]+' erros.spotdl | sort -u)
        if [ ${#failed_urls[@]} -gt 0 ]; then
            if [ "$QUIET" = false ]; then
                echo -e "${ICON_INFO} Rescuing ${#failed_urls[@]} track(s) from erros.spotdl..." >&2
            fi
            run_spotdl save "${failed_urls[@]}" --save-file "$batch_meta" >/dev/null 2>&1 || true
            [ -s "$batch_meta" ] && has_targets=true
        fi
    elif [ -n "$target" ] && [ -f "$target" ]; then
        batch_meta="$target"
        has_targets=true
    fi

    if [ "$has_targets" = true ]; then
        run_py "$SCRIPT_DIR/src/modules/fallback.py" \
            "$batch_meta" \
            "$TEMP_DIR" \
            "" \
            "$THREADS" \
            "$SYNCED_ONLY" \
            "$AUDIO_FORMAT" \
            "${YTDLP_JS_ARGS[*]:-}"
        rm -f erros.spotdl
    else
        echo -e "${ICON_OK} No pending failed tracks to rescue."
    fi
}

# --- STATUS & ANALYTICS ORCHESTRATION ---
orchestrate_status() {
    local target_dir="${1:-$(resolve_music_root)}"
    local extra_args=()
    [ "$OUTPUT_FORMAT" = "json" ] && extra_args+=(--json)
    [ "$OUTPUT_FORMAT" = "plain" ] && extra_args+=(--plain)

    run_py "$SCRIPT_DIR/src/modules/stats.py" -r "$target_dir" "${extra_args[@]}"
}

# --- DEDUPLICATION ORCHESTRATION ---
orchestrate_dedup() {
    local target_dir="${1:-$(resolve_music_root)}"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/src/modules/dedup.py" -r "$target_dir" $dry_flag
    cleanup_empty_dirs
}

# --- PATCH ORCHESTRATION ---
orchestrate_patch() {
    setup_environment
    local patch_fmt="${COMMAND_ARGS[0]:-${AUDIO_FORMAT:-flac}}"
    local patch_target="${COMMAND_ARGS[1]:-}"

    validate_format "$patch_fmt"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="true" || dry_flag="false"
    local keep_flag=""
    [ "$KEEP_OLD" = true ] && keep_flag="true" || keep_flag="false"
    local yes_flag=""
    [ "$ASSUME_YES" = true ] && yes_flag="true" || yes_flag="false"

    if [ "$QUIET" = false ]; then
        echo -e "${ICON_DISC} Upgrading audio format to ${BOLD}${patch_fmt^^}${RESET}..." >&2
    fi

    run_py "$SCRIPT_DIR/src/patch/cli.py" \
        "$patch_fmt" \
        "$TEMP_DIR" \
        "$THREADS" \
        "$keep_flag" \
        "$dry_flag" \
        "$patch_target" \
        "${YTDLP_JS_ARGS[*]:-}" \
        "$yes_flag"

    cleanup_empty_dirs
    echo -e "${GREEN}${ICON_OK} Audio format patch completed successfully.${RESET}"
}

# --- FULL OPTIMIZATION PIPELINE ---
orchestrate_optimize() {
    local target_dir="${1:-$(resolve_music_root)}"
    if [ "$QUIET" = false ]; then
        echo -e "${ICON_DISC} Running Rockbox library optimization pipeline on: ${BOLD}$target_dir${RESET}" >&2
    fi

    orchestrate_dedup "$target_dir"
    orchestrate_covers "optimize" "$target_dir"
    orchestrate_tags "fix" "$target_dir"
    orchestrate_playlist "repair"
    cleanup_empty_dirs

    echo -e "${GREEN}${ICON_OK} Library optimization pipeline completed.${RESET}"
}

# --- LIBRARY ORCHESTRATION ---
orchestrate_library() {
    local action="${1:-${SUBACTION:-}}"
    local music_root
    music_root="$(resolve_music_root)"

    case "$action" in
        status)
            orchestrate_status "$music_root"
            ;;
        audit)
            local audit_args=("-r" "$music_root")
            [ "$OUTPUT_FORMAT" = "json" ] && audit_args+=(--json)
            run_py "$SCRIPT_DIR/src/modules/audit.py" "${audit_args[@]}"
            ;;
        dedup)
            orchestrate_dedup "$music_root"
            ;;
        optimize)
            orchestrate_optimize "$music_root"
            ;;
        patch)
            orchestrate_patch "${COMMAND_ARGS[@]:-}"
            ;;
        fix)
            local dry_flag=""
            [ "$DRY_RUN" = true ] && dry_flag="--dry-run"
            run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" -r "$music_root" $dry_flag
            ;;
        romaji)
            local romaji_args=("-r" "$music_root" "-t" "$THREADS" "-a")
            [ "$DRY_RUN" = true ] && romaji_args+=("-n")
            run_py "$SCRIPT_DIR/src/romaji/cli.py" "${romaji_args[@]}"
            ;;
        *)
            error_dual "Invalid library action '$action'" "Supported actions: status, audit, dedup, optimize, patch, fix, romaji" "syncdap library $action" "" "Run 'syncdap library --help'"
            exit 2
            ;;
    esac
}

# --- ARTIST ORCHESTRATION ---
orchestrate_artist() {
    local action="${1:-${SUBACTION:-}}"
    local target="${2:-${COMMAND_ARGS[0]:-}}"
    local music_root
    music_root="$(resolve_music_root)"

    local artist_dir=""
    if [ -d "$target" ]; then
        artist_dir="$(readlink -f "$target")"
    else
        artist_dir=$(find "$music_root" -mindepth 1 -maxdepth 2 -type d -iname "*$target*" 2>/dev/null | head -n 1)
    fi

    if [ -z "$artist_dir" ] || [ ! -d "$artist_dir" ]; then
        error_dual "Artist not found" "No directory matching '$target' found in library" "$target" "" "Specify a valid artist directory or name within $music_root"
        exit 1
    fi

    case "$action" in
        status)
            orchestrate_status "$artist_dir"
            ;;
        audit)
            local audit_args=("-r" "$artist_dir")
            [ "$OUTPUT_FORMAT" = "json" ] && audit_args+=(--json)
            run_py "$SCRIPT_DIR/src/modules/audit.py" "${audit_args[@]}"
            ;;
        dedup)
            orchestrate_dedup "$artist_dir"
            ;;
        fix)
            local dry_flag=""
            [ "$DRY_RUN" = true ] && dry_flag="--dry-run"
            run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" -r "$artist_dir" $dry_flag
            ;;
        romaji)
            local romaji_args=("-r" "$music_root" "-t" "$THREADS" "-p" "$artist_dir")
            [ "$DRY_RUN" = true ] && romaji_args+=("-n")
            run_py "$SCRIPT_DIR/src/romaji/cli.py" "${romaji_args[@]}"
            ;;
        patch)
            local patch_fmt="${COMMAND_ARGS[0]:-${AUDIO_FORMAT:-flac}}"
            COMMAND_ARGS=("$patch_fmt" "$artist_dir")
            orchestrate_patch "${COMMAND_ARGS[@]}"
            ;;
        *)
            error_dual "Invalid artist action '$action'" "Supported actions: status, audit, dedup, fix, romaji, patch" "syncdap artist $action" "" "Run 'syncdap artist --help'"
            exit 2
            ;;
    esac
}

# --- ALBUM ORCHESTRATION ---
orchestrate_album() {
    local action="${1:-${SUBACTION:-}}"
    local target="${2:-${COMMAND_ARGS[0]:-}}"
    local music_root
    music_root="$(resolve_music_root)"

    local album_dir=""
    if [ -n "$target" ]; then
        if [ -d "$target" ] || [ -f "$target" ]; then
            album_dir="$(readlink -f "$target")"
        else
            album_dir=$(find "$music_root" -mindepth 1 -maxdepth 3 -type d -iname "*$target*" 2>/dev/null | head -n 1)
        fi
    fi
    [ -z "$album_dir" ] && album_dir="$music_root"

    case "$action" in
        status)
            orchestrate_status "$album_dir"
            ;;
        audit)
            local audit_args=("-r" "$album_dir")
            [ "$OUTPUT_FORMAT" = "json" ] && audit_args+=(--json)
            run_py "$SCRIPT_DIR/src/modules/audit.py" "${audit_args[@]}"
            ;;
        dedup)
            orchestrate_dedup "$album_dir"
            ;;
        expand)
            local expand_args=("-r" "$music_root" "-t" "$THREADS")
            [ "$DRY_RUN" = true ] && expand_args+=(--dry-run)
            [ "$ASSUME_YES" = true ] && expand_args+=(--yes)
            [ -n "$AUDIO_FORMAT" ] && expand_args+=("-F" "$AUDIO_FORMAT")
            [ "$SYNCED_ONLY" = true ] && expand_args+=(--synced-only)

            if [ -n "$target" ] && [ -f "$target" ]; then
                expand_args+=("$target")
            fi
            run_py "$SCRIPT_DIR/src/modules/album_expander.py" "${expand_args[@]}"
            ;;
        optimize)
            orchestrate_optimize "$album_dir"
            ;;
        fix)
            local dry_flag=""
            [ "$DRY_RUN" = true ] && dry_flag="--dry-run"
            run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" -r "$album_dir" $dry_flag
            ;;
        romaji)
            local romaji_args=("-r" "$music_root" "-t" "$THREADS" "-p" "$album_dir")
            [ "$DRY_RUN" = true ] && romaji_args+=("-n")
            run_py "$SCRIPT_DIR/src/romaji/cli.py" "${romaji_args[@]}"
            ;;
        patch)
            local patch_fmt="${COMMAND_ARGS[0]:-${AUDIO_FORMAT:-flac}}"
            COMMAND_ARGS=("$patch_fmt" "$album_dir")
            orchestrate_patch "${COMMAND_ARGS[@]}"
            ;;
        *)
            error_dual "Invalid album action '$action'" "Supported actions: status, audit, dedup, expand, optimize, patch, fix, romaji" "syncdap album $action" "" "Run 'syncdap album --help'"
            exit 2
            ;;
    esac
}

# --- TRACK ORCHESTRATION ---
orchestrate_track() {
    local action="${1:-${SUBACTION:-}}"
    local target="${2:-${COMMAND_ARGS[0]:-}}"

    if [ -z "$target" ] || [ ! -f "$target" ]; then
        error_dual "Audio file not found" "Track operations require a valid audio file" "$target" "" "Pass a valid file path: syncdap track $action '/path/to/song.flac'"
        exit 1
    fi
    local track_path
    track_path="$(readlink -f "$target")"

    case "$action" in
        status)
            orchestrate_status "$track_path"
            ;;
        audit)
            local audit_args=("-r" "$track_path")
            [ "$OUTPUT_FORMAT" = "json" ] && audit_args+=(--json)
            run_py "$SCRIPT_DIR/src/modules/audit.py" "${audit_args[@]}"
            ;;
        expand)
            local expand_args=("-r" "$(dirname "$track_path")" "-t" "$THREADS" "$track_path")
            [ "$DRY_RUN" = true ] && expand_args+=(--dry-run)
            [ "$ASSUME_YES" = true ] && expand_args+=(--yes)
            [ -n "$AUDIO_FORMAT" ] && expand_args+=("-F" "$AUDIO_FORMAT")
            [ "$SYNCED_ONLY" = true ] && expand_args+=(--synced-only)
            run_py "$SCRIPT_DIR/src/modules/album_expander.py" "${expand_args[@]}"
            ;;
        patch)
            local patch_fmt="${COMMAND_ARGS[1]:-${AUDIO_FORMAT:-flac}}"
            COMMAND_ARGS=("$patch_fmt" "$track_path")
            orchestrate_patch "${COMMAND_ARGS[@]}"
            ;;
        romaji)
            local romaji_args=("-r" "$(dirname "$track_path")" "-t" "$THREADS" "-p" "$track_path")
            [ "$DRY_RUN" = true ] && romaji_args+=("-n")
            run_py "$SCRIPT_DIR/src/romaji/cli.py" "${romaji_args[@]}"
            ;;
        *)
            error_dual "Invalid track action '$action'" "Supported actions: status, audit, expand, patch, romaji" "syncdap track $action" "" "Run 'syncdap track --help'"
            exit 2
            ;;
    esac
}

# --- COVERS HIERARCHY ORCHESTRATION (optimize | embed) ---
orchestrate_covers() {
    setup_environment
    local action="${1:-${SUBACTION:-}}"
    local target_scope="${2:-all}"
    local music_root
    music_root="$(resolve_music_root)"
    local dirs_file="$TEMP_DIR/cover_dirs.txt"

    case "$action" in
        optimize|strip)
            find "$music_root" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.opus" \) ! -path "*/Playlists/*" -exec dirname {} + 2>/dev/null | sort -u > "$dirs_file"
            run_py "$SCRIPT_DIR/src/modules/covers.py" "optimize" "$dirs_file" "$THREADS"
            ;;
        embed)
            find "$music_root" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.opus" \) ! -path "*/Playlists/*" -exec dirname {} + 2>/dev/null | sort -u > "$dirs_file"
            run_py "$SCRIPT_DIR/src/modules/covers.py" "embed" "$dirs_file" "$THREADS"
            ;;
        *)
            error_dual "Invalid covers action '$action'" "Available covers actions are 'optimize' and 'embed'" "syncdap covers $action" "" "Usage: syncdap covers <optimize | embed>"
            exit 2
            ;;
    esac
}

# --- LYRICS HIERARCHY ORCHESTRATION (fetch | embed) ---
orchestrate_lyrics() {
    setup_environment
    local action="${1:-${SUBACTION:-}}"
    local music_root
    music_root="$(resolve_music_root)"
    local dirs_file="$TEMP_DIR/lyrics_dirs.txt"

    find "$music_root" -mindepth 1 -type d ! -path "*/Playlists*" 2>/dev/null | sort > "$dirs_file"

    case "$action" in
        fetch|scan)
            run_py "$SCRIPT_DIR/src/modules/lyrics.py" "$dirs_file" "$THREADS" "$SYNCED_ONLY"
            ;;
        embed)
            run_py "$SCRIPT_DIR/src/modules/lyrics.py" "$dirs_file" "$THREADS" "$SYNCED_ONLY" --embed
            ;;
        *)
            error_dual "Invalid lyrics action '$action'" "Available lyrics actions are 'fetch' and 'embed'" "syncdap lyrics $action" "" "Usage: syncdap lyrics <fetch | embed>"
            exit 2
            ;;
    esac
}

# --- PLAYLIST HIERARCHY ORCHESTRATION (manage | merge | delete | repair) ---
orchestrate_playlist() {
    local action="${1:-${SUBACTION:-}}"
    local music_root
    music_root="$(resolve_music_root)"

    case "$action" in
        manage)
            local pl_target="${COMMAND_ARGS[0]:-}"
            local pl_args=(--menu)
            [ -n "$pl_target" ] && pl_args=(--name "$pl_target")
            run_py "$SCRIPT_DIR/src/playlists/cli.py" "${pl_args[@]}"
            ;;
        merge)
            if [ ${#COMMAND_ARGS[@]} -lt 2 ]; then
                error_dual "Missing playlist merge targets" "Two source playlists are required" "syncdap playlist merge <p1> <p2> [out]" "" "Example: syncdap playlist merge Favorites.m3u8 Rock.m3u8 Merged.m3u8"
                exit 2
            fi
            local p1="${COMMAND_ARGS[0]}"
            local p2="${COMMAND_ARGS[1]}"
            local out="${COMMAND_ARGS[2]:-}"
            local yes_flag=""
            [ "$ASSUME_YES" = true ] && yes_flag="--yes"
            run_py "$SCRIPT_DIR/src/playlists/cli.py" --merge "$p1" "$p2" ${out:+"$out"} $yes_flag
            ;;
        delete)
            local del_target="${COMMAND_ARGS[0]:-}"
            if [ -z "$del_target" ]; then
                error_dual "Missing playlist to delete" "A playlist name or file path is required" "syncdap playlist delete <name>" "" "Example: syncdap playlist delete OldParty.m3u8"
                exit 2
            fi
            local yes_flag=""
            [ "$ASSUME_YES" = true ] && yes_flag="--yes"
            run_py "$SCRIPT_DIR/src/playlists/cli.py" --delete "$del_target" $yes_flag
            ;;
        repair)
            local dry_flag=""
            [ "$DRY_RUN" = true ] && dry_flag="--dry-run"
            run_py "$SCRIPT_DIR/src/modules/playlist_repair.py" -r "$music_root" $dry_flag
            ;;
        *)
            error_dual "Invalid playlist action '$action'" "Available playlist actions are 'manage', 'merge', 'delete', 'repair'" "syncdap playlist $action" "" "Usage: syncdap playlist <manage [name] | merge <p1> <p2> [out] | delete <name> | repair>"
            exit 2
            ;;
    esac
}

# --- TAGS HIERARCHY ORCHESTRATION (fix | genres | romaji) ---
orchestrate_tags() {
    setup_environment
    local action="${1:-${SUBACTION:-}}"
    local music_root
    music_root="$(resolve_music_root)"

    case "$action" in
        fix)
            local dry_flag=""
            [ "$DRY_RUN" = true ] && dry_flag="--dry-run"
            run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" -r "$music_root" $dry_flag
            ;;
        genres)
            local dirs_file="$TEMP_DIR/genre_dirs.txt"
            find "$music_root" -mindepth 1 -type d ! -path "*/Playlists*" 2>/dev/null | sort > "$dirs_file"
            run_py "$SCRIPT_DIR/src/modules/genres.py" "$dirs_file" "$THREADS"
            ;;
        romaji)
            local romaji_target="${COMMAND_ARGS[0]:-}"
            local romaji_args=("-r" "$music_root" "-t" "$THREADS")
            [ "$DRY_RUN" = true ] && romaji_args+=("-n")
            if [ -n "$romaji_target" ]; then
                romaji_args+=("-p" "$romaji_target")
            else
                romaji_args+=("-a")
            fi
            run_py "$SCRIPT_DIR/src/romaji/cli.py" "${romaji_args[@]}"
            ;;
        *)
            error_dual "Invalid tags action '$action'" "Available tags actions are 'fix', 'genres', 'romaji'" "syncdap tags $action" "" "Usage: syncdap tags <fix | genres | romaji [target]>"
            exit 2
            ;;
    esac
}

# --- SCROBBLER ORCHESTRATION (sync | auth | status | logout) ---
orchestrate_scrobbler() {
    setup_environment
    local action="${1:-${SUBACTION:-sync}}"
    local scrobbler_args=("$action")

    [ -n "$TARGET_ROOT" ] && scrobbler_args+=("-r" "$TARGET_ROOT")
    [ "$DRY_RUN" = true ] && scrobbler_args+=("-n")
    [ "$ASSUME_YES" = true ] && scrobbler_args+=("-y")
    [ "$VERBOSE" = true ] && scrobbler_args+=("-v")
    [ "$QUIET" = true ] && scrobbler_args+=("-q")
    [ "$OUTPUT_FORMAT" = "json" ] && scrobbler_args+=("--json")
    [ "$OUTPUT_FORMAT" = "plain" ] && scrobbler_args+=("--plain")
    [ -n "${TZ_OFFSET:-}" ] && scrobbler_args+=("--tz-offset" "$TZ_OFFSET")
    [ "${KEEP_LOG:-false}" = true ] && scrobbler_args+=("--keep-log")
    [ -n "${CONFIG_FILE:-}" ] && scrobbler_args+=("-c" "$CONFIG_FILE")

    if [ ${#COMMAND_ARGS[@]} -gt 0 ]; then
        scrobbler_args+=("${COMMAND_ARGS[@]}")
    fi

    run_py "$SCRIPT_DIR/src/scrobbler/cli.py" "${scrobbler_args[@]}"
}

