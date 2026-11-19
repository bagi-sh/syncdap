#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/orchestrator.sh
# Purpose: Execution coordinator for media processing submodules
# ==============================================================================

# --- FALLBACK RESCUE ORCHESTRATION ---
run_fallback_rescue() {
    local batch_meta="$TEMP_DIR/batch_meta.spotdl"
    local has_targets=false

    if [ "$FALLBACK_ONLY" = true ] && [ -n "$CLEAN_URL" ]; then
        echo ""
        echo -e "${CYAN}⚡ Fallback mode: Fetching Spotify metadata...${RESET}"
        run_spotdl save "$CLEAN_URL" --save-file "$batch_meta" >/dev/null 2>&1 || true
        [ -s "$batch_meta" ] && has_targets=true
    elif [ -s "erros.spotdl" ]; then
        echo ""
        echo -e "${YELLOW}⚠️ [3/5] Starting smart parallel fallback for failed tracks...${RESET}"
        mapfile -t failed_urls < <(grep -oE 'https://open\.spotify\.com/track/[a-zA-Z0-9]+' erros.spotdl | sort -u)
        if [ ${#failed_urls[@]} -gt 0 ]; then
            echo "   Found ${#failed_urls[@]} track(s) for recovery."
            echo "   Fetching official metadata from Spotify..."
            run_spotdl save "${failed_urls[@]}" --save-file "$batch_meta" >/dev/null 2>&1 || true
            [ -s "$batch_meta" ] && has_targets=true
        fi
    fi

    if [ "$has_targets" = true ]; then
        run_py "$SCRIPT_DIR/src/modules/fallback.py" \
            "$batch_meta" \
            "$TEMP_DIR" \
            "$TARGET_M3U" \
            "$THREADS" \
            "$SYNCED_ONLY" \
            "$AUDIO_EXT" \
            "${YTDLP_JS_ARGS[*]:-}"
        rm -f erros.spotdl
    else
        if [ "$FALLBACK_ONLY" = false ]; then
            echo ""
            echo -e "${GREEN}✅ [3/5] No failed tracks registered by spotDL.${RESET}"
        fi
    fi
}

# --- DEDUPLICATION ORCHESTRATION ---
orchestrate_dedup() {
    local target_dir
    target_dir="$(resolve_music_root)"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/src/modules/dedup.py" -r "$target_dir" $dry_flag
}

# --- ROCKBOX METADATA ORCHESTRATION ---
orchestrate_rockbox_tags() {
    local target_dir
    target_dir="$(resolve_music_root)"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" -r "$target_dir" $dry_flag
}

# --- LIBRARY STATUS & ANALYTICS ORCHESTRATION ---
orchestrate_status() {
    local target_dir
    target_dir="$(resolve_music_root)"
    run_py "$SCRIPT_DIR/src/modules/stats.py" -r "$target_dir"
}

# --- PLAYLIST AUDIT & REPAIR ORCHESTRATION ---
orchestrate_playlist_repair() {
    local target_dir
    target_dir="$(resolve_music_root)"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/src/modules/playlist_repair.py" -r "$target_dir" $dry_flag
}

# --- COVER ART ORCHESTRATION ---
orchestrate_covers() {
    local mode="${1:-embed}"    # 'embed' or 'optimize'
    local scope="${2:-session}" # 'all' or 'session'
    local dirs_file="$TEMP_DIR/cover_dirs.txt"
    local music_root
    music_root="$(resolve_music_root)"

    echo ""
    if [ "$scope" = "all" ]; then
        find "$music_root" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.opus" \) ! -path "*/Playlists/*" -exec dirname {} + 2>/dev/null | sort -u > "$dirs_file"
    else
        find "$music_root" -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.opus" \) ! -path "*/Playlists/*" -newer "$MARKER" -exec dirname {} + 2>/dev/null | sort -u > "$dirs_file"
    fi

    run_py "$SCRIPT_DIR/src/modules/covers.py" "$mode" "$dirs_file" "$THREADS"
}

# --- GENRE ENRICHMENT ORCHESTRATION ---
orchestrate_genres() {
    local scope="${1:-session}" # 'all' or 'session'
    local dirs_file="$TEMP_DIR/genre_dirs.txt"

    echo ""
    if [ "$scope" = "all" ]; then
        echo -e "${MAGENTA}🏷️ Enriching genre metadata across the entire library (album-by-album)...${RESET}"
        find . -mindepth 2 -maxdepth 2 -type d ! -path "./Playlists*" | sort > "$dirs_file"
    else
        echo -e "${MAGENTA}🏷️ [5/5] Checking and enriching genre metadata for downloaded albums...${RESET}"
        find . -mindepth 2 -maxdepth 2 -type d ! -path "./Playlists*" -newer "$MARKER" | sort > "$dirs_file"
    fi

    run_py "$SCRIPT_DIR/src/modules/genres.py" "$dirs_file" "$THREADS"
}

# --- LYRICS SCANNER ORCHESTRATION ---
orchestrate_lyrics() {
    local scope="${1:-session}" # 'all' or 'session'
    local dirs_file="$TEMP_DIR/lyrics_dirs.txt"

    echo ""
    echo -e "${CYAN}🎵 Scanning for tracks with missing .lrc lyrics...${RESET}"
    if [ "$scope" = "all" ]; then
        find . -mindepth 2 -maxdepth 2 -type d ! -path "./Playlists*" | sort > "$dirs_file"
    else
        find . -mindepth 2 -maxdepth 2 -type d ! -path "./Playlists*" -newer "$MARKER" | sort > "$dirs_file"
    fi

    run_py "$SCRIPT_DIR/src/modules/lyrics.py" "$dirs_file" "$THREADS" "$SYNCED_ONLY"
}

# --- METADATA LYRICS EMBEDDING ORCHESTRATION ---
orchestrate_embed_lyrics() {
    local music_root
    music_root="$(resolve_music_root)"
    local dirs_file="$TEMP_DIR/embed_lyrics_dirs.txt"

    echo ""
    echo -e "${CYAN}📝 Scanning and embedding lyrics directly into audio metadata...${RESET}"
    find "$music_root" -mindepth 1 -type d ! -path "*/Playlists*" 2>/dev/null | sort > "$dirs_file"

    run_py "$SCRIPT_DIR/src/modules/lyrics.py" "$dirs_file" "$THREADS" "$SYNCED_ONLY" --embed
}

# --- ALBUM EXPANDER ORCHESTRATION ---
orchestrate_expand_albums() {
    local music_root
    music_root="$(resolve_music_root)"
    local target_file="${EXPAND_TARGET:-$SPLIT_FILE}"

    local expand_args=("-r" "$music_root" "-t" "$THREADS")
    [ "$DRY_RUN" = true ] && expand_args+=(--dry-run)
    [ "$ASSUME_YES" = true ] && expand_args+=(--yes)
    [ -n "$AUDIO_FORMAT" ] && expand_args+=("-F" "$AUDIO_FORMAT")
    [ "$SYNCED_ONLY" = true ] && expand_args+=(--synced-only)

    if [ -n "$target_file" ]; then
        if [ ! -f "$target_file" ]; then
            echo -e "${RED}❌ Error: Specified file does not exist: $target_file${RESET}" >&2
            exit 1
        fi
        expand_args+=("$target_file")
    fi

    run_py "$SCRIPT_DIR/src/modules/album_expander.py" "${expand_args[@]}"
}

orchestrate_split() {
    orchestrate_expand_albums
}

# --- DURATION ANOMALY AUDITOR ORCHESTRATION ---
orchestrate_audit_duration() {
    local music_root
    music_root="$(resolve_music_root)"
    run_py "$SCRIPT_DIR/src/modules/audit.py" -r "$music_root" --auto-expand
}

# --- NAME SEARCH & RESOLUTION ORCHESTRATION ---
orchestrate_search_download() {
    local query="$SEARCH_QUERY"
    echo ""
    echo -e "${BOLD}${BLUE}🔍 Resolving music metadata for:${RESET} ${CYAN}'$query'${RESET}"

    local meta_json
    meta_json="$(run_py "$SCRIPT_DIR/src/modules/search.py" "$query" --json 2>/dev/null)"

    if [ -z "$meta_json" ] || [ "$meta_json" = "null" ]; then
        echo -e "${RED}❌ Error: Could not resolve metadata for '$query'.${RESET}" >&2
        exit 1
    fi

    local meta_file="$TEMP_DIR/search_resolved.json"
    echo "$meta_json" > "$meta_file"

    echo -e "${GREEN}✅ Resolved metadata. Starting high-precision download...${RESET}"
    orchestrate_fallback "$meta_file"
}
