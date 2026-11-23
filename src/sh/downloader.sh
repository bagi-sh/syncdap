#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/downloader.sh
# Purpose: Primary download orchestration via spotDL with format & bitrate control
# ==============================================================================

run_spotdl_download() {
    if [ "$QUIET" = false ]; then
        echo -e "${BLUE}${ICON_DL} [1/5] Starting primary download via spotDL...${RESET}" >&2
        echo -e "   Target:  ${BOLD}$CLEAN_URL${RESET}" >&2
        echo -e "   Format:  ${GREEN}${AUDIO_EXT} (highest quality)${RESET}" >&2
        echo -e "   Threads: ${BOLD}$THREADS${RESET}" >&2
    fi

    rm -f erros.spotdl

    local is_playlist=false
    if [[ "$CLEAN_URL" =~ /playlist/ ]]; then
        is_playlist=true
    fi

    local spotdl_providers="${SPOTDL_PROVIDERS:-youtube youtube-music soundcloud bandcamp}"
    local spotdl_max_retries="${SPOTDL_MAX_RETRIES:-1}"
    local spotdl_throttled_rate="${SPOTDL_THROTTLED_RATE:-100K}"

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
        --audio $spotdl_providers
        --max-retries "$spotdl_max_retries"
        --save-errors erros.spotdl
        --respect-skip-file
        --yt-dlp-args "--cookies-from-browser firefox --throttled-rate $spotdl_throttled_rate"
    )

    if [ "$is_playlist" = true ]; then
        spotdl_cmd+=(--m3u "{list}.m3u8")
    fi

    "${spotdl_cmd[@]}" || true
}
