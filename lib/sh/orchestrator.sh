#!/usr/bin/env bash
# ==============================================================================
# Module: lib/sh/orchestrator.sh
# Purpose: Execution coordinator for media processing submodules
# ==============================================================================

# --- FALLBACK RESCUE ORCHESTRATION ---
run_fallback_rescue() {
    local batch_meta="$TEMP_DIR/batch_meta.spotdl"
    local has_targets=false

    if [ "$FALLBACK_ONLY" = true ] && [ -n "$CLEAN_URL" ]; then
        echo ""
        echo -e "${CYAN}⚡ Fallback mode: Fetching Spotify metadata...${RESET}"
        spotdl save "$CLEAN_URL" --save-file "$batch_meta" >/dev/null 2>&1 || true
        [ -s "$batch_meta" ] && has_targets=true
    elif [ -s "erros.spotdl" ]; then
        echo ""
        echo -e "${YELLOW}⚠️ [3/5] Starting smart parallel fallback for failed tracks...${RESET}"
        mapfile -t failed_urls < <(grep -oE 'https://open\.spotify\.com/track/[a-zA-Z0-9]+' erros.spotdl | sort -u)
        if [ ${#failed_urls[@]} -gt 0 ]; then
            echo "   Found ${#failed_urls[@]} track(s) for recovery."
            echo "   Fetching official metadata from Spotify..."
            spotdl save "${failed_urls[@]}" --save-file "$batch_meta" >/dev/null 2>&1 || true
            [ -s "$batch_meta" ] && has_targets=true
        fi
    fi

    if [ "$has_targets" = true ]; then
        run_py "$SCRIPT_DIR/lib/fallback.py" \
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

    run_py "$SCRIPT_DIR/lib/dedup.py" -r "$target_dir" $dry_flag
}

# --- ROCKBOX METADATA ORCHESTRATION ---
orchestrate_rockbox_tags() {
    local target_dir
    target_dir="$(resolve_music_root)"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/lib/rockbox_tags.py" -r "$target_dir" $dry_flag
}

# --- LIBRARY STATUS & ANALYTICS ORCHESTRATION ---
orchestrate_status() {
    local target_dir
    target_dir="$(resolve_music_root)"
    run_py "$SCRIPT_DIR/lib/stats.py" -r "$target_dir"
}

# --- PLAYLIST AUDIT & REPAIR ORCHESTRATION ---
orchestrate_playlist_repair() {
    local target_dir
    target_dir="$(resolve_music_root)"
    local dry_flag=""
    [ "$DRY_RUN" = true ] && dry_flag="--dry-run"

    run_py "$SCRIPT_DIR/lib/playlist_repair.py" -r "$target_dir" $dry_flag
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

    run_py "$SCRIPT_DIR/lib/covers.py" "$mode" "$dirs_file" "$THREADS"
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

    run_py "$SCRIPT_DIR/lib/genres.py" "$dirs_file" "$THREADS"
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

    run_py "$SCRIPT_DIR/lib/lyrics.py" "$dirs_file" "$THREADS" "$SYNCED_ONLY"
}
