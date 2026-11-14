#!/usr/bin/env bash
# ==============================================================================
# Module: src/downloader.sh
# Purpose: Primary download orchestration via spotDL with format & bitrate control
# ==============================================================================

run_spotdl_download() {
    echo ""
    echo -e "${BLUE}📥 [1/5] Starting primary download via spotDL...${RESET}"
    echo -e "   Target:  ${BOLD}$CLEAN_URL${RESET}"
    echo -e "   Format:  ${GREEN}${AUDIO_EXT} (highest quality)${RESET}"
    echo -e "   Threads: ${BOLD}$THREADS${RESET}"

    rm -f erros.spotdl

    local is_playlist=false
    if [[ "$CLEAN_URL" =~ /playlist/ ]]; then
        is_playlist=true
    fi

    local spotdl_cmd=(
        run_spotdl
        "$CLEAN_URL"
        "${SPOTDL_FORMAT_ARGS[@]}"
        --threads "$THREADS"
        --output "{artist}/{album}/{track-number} {title} - {artist}.{output-ext}"
        --detect-formats mp3 flac m4a ogg opus wav
        --scan-for-songs
        --overwrite skip
        --generate-lrc
        --audio youtube youtube-music soundcloud bandcamp
        --max-retries 1
        --save-errors erros.spotdl
        --respect-skip-file
        --yt-dlp-args "--cookies-from-browser firefox --throttled-rate 100K"
    )

    if [ "$is_playlist" = true ]; then
        spotdl_cmd+=(--m3u "{list}.m3u8")
    fi

    "${spotdl_cmd[@]}" || true
}
