#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/cli.sh
# Purpose: CLI help presentation and command-line argument parsing
# ==============================================================================

show_help() {
    cat << 'EOF'
Usage: syncdap [OPTIONS] <URL> | [COMMAND] [OPTIONS]

Commands:
  <URL>                        Download album, playlist, or track from Spotify
  -p, --patch [FMT] [TARGET]   Upgrade library/playlist audio format (default: flac)
  -R, --romaji [TARGET]        Transliterate Japanese tags/paths to Hepburn Romaji
  -P, --playlist [NAME]        Interactive playlist manager (create/edit/delete)
  -M, --merge PL1 PL2 [OUT]    Merge two playlists and deduplicate tracks
  -D, --delete [PLAYLIST]      Delete a playlist and prompt to purge audio files
  -o, --optimize               Optimize for Rockbox/DAP (strip art, dedup, fix tags)
  -e, --embed                  Re-embed cover.jpg art into audio files
  --dedup                      Deduplicate tracks keeping highest audio quality
  --fix-tags                   Audit and unify album/artist tags for Rockbox
  --repair-playlists           Relink moved/renamed tracks and prune dead paths
  -g, --genres                 Enrich genre tags via iTunes, Deezer & MusicBrainz
  -l, --lyrics                 Scan and download missing timestamped .lrc lyrics
  -s, --status                 Show music library health and statistics dashboard
  -f, --fallback [URL]         Direct yt-dlp rescue (or retry erros.spotdl)
  --split <FILE>               Split single-file full album into individual tracks
  --audit-duration             Audit library tracks >10m to detect accidental full-album rips
  --embed-lyrics               Scan library and embed lyrics directly into audio metadata
  --search <QUERY>             Search track/album by name without URL
  --update                     Update syncdap to latest git commits and tools
  --uninstall                  Completely remove syncdap from system

Options:
  -a, --all                    Apply to entire music library root
  -d, --dry-run                Preview actions without modifying files on disk
  -y, --yes                    Skip confirmation prompts (non-interactive)
  -F, --format <FMT>           Audio format: flac, mp3, m4a, opus, ogg, wav
  -P, --playlist <NAME>        Target specific playlist (.m3u8)
  -r, --root-dir <DIR>         Music library / DAP mount directory (default: .)
  -t, --threads <NUM>          Worker thread concurrency (default: 4)
  --cue <FILE.cue>             Path to CUE sheet for album splitting
  --tracklist <FILE.txt>       Path to timestamped tracklist for album splitting
  --allow-live                 Allow live versions in candidate filter
  --allow-remix                Allow remixes in candidate filter
  --synced-only                Only fetch timestamped [mm:ss] synced lyrics
  --keep-old                   Retain original files during patch/upgrade
  -h, --help                   Display this help message
EOF
}

parse_arguments() {
    if [ $# -eq 0 ]; then
        echo -e "${RED}❌ Error: No URL or command provided.${RESET}"
        echo ""
        show_help
        exit 1
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            --update)
                UPDATE_MODE=true
                shift 1
                ;;
            --uninstall|--unistall)
                UNINSTALL_MODE=true
                shift 1
                ;;
            -F|--format)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --format requires an argument (flac, mp3, m4a, opus, ogg, wav).${RESET}"
                    exit 1
                fi
                AUDIO_FORMAT="$2"
                PATCH_FORMAT="$2"
                shift 2
                ;;
            -p|--patch|-u|--upgrade)
                PATCH_MODE=true
                if [[ $# -gt 1 ]] && ! [[ "$2" =~ ^- ]]; then
                    PATCH_FORMAT="$2"
                    shift 2
                else
                    PATCH_FORMAT="${PATCH_FORMAT:-flac}"
                    shift 1
                fi
                ;;
            -R|--romaji|--transliterate|--rockbox-romaji)
                ROMAJI_MODE=true
                DO_ROMAJI=true
                shift 1
                if [[ $# -gt 0 ]] && ! [[ "$1" =~ ^- ]]; then
                    ROMAJI_TARGET="$1"
                    shift 1
                fi
                ;;
            -P|--playlist)
                if [[ $# -gt 1 ]] && ! [[ "$2" =~ ^- ]]; then
                    PLAYLIST_NAME="$2"
                    shift 2
                else
                    PLAYLIST_MANAGER_MODE=true
                    shift 1
                fi
                ;;
            -D|--delete|--delete-playlist)
                DELETE_PLAYLIST_MODE=true
                if [[ $# -gt 1 ]] && ! [[ "$2" =~ ^- ]]; then
                    DELETE_PLAYLIST_TARGET="$2"
                    shift 2
                else
                    shift 1
                fi
                ;;
            -M|--merge|--merge-playlists)
                MERGE_PLAYLIST_MODE=true
                if [[ $# -lt 3 ]] || [[ "$2" =~ ^- ]] || [[ "$3" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --merge requires two source playlist names (e.g. 'syncdap --merge pl1 pl2 [out]').${RESET}"
                    exit 1
                fi
                MERGE_PL1="$2"
                MERGE_PL2="$3"
                shift 3
                if [[ $# -gt 0 ]] && ! [[ "$1" =~ ^- ]]; then
                    MERGE_OUT="$1"
                    shift 1
                fi
                ;;
            -r|--root-dir)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --root-dir requires a directory path.${RESET}"
                    exit 1
                fi
                ROMAJI_ROOT="$2"
                TARGET_ROOT="$2"
                shift 2
                ;;
            --dedup|--deduplicate)
                DEDUP_MODE=true
                shift 1
                ;;
            --fix-tags|--rockbox-tags|--metadata)
                FIX_TAGS_MODE=true
                shift 1
                ;;
            -s|--status|--stats)
                STATUS_MODE=true
                shift 1
                ;;
            --repair-playlists|--playlists-repair)
                REPAIR_PLAYLISTS_MODE=true
                shift 1
                ;;
            -a|--all)
                ALL_MODE=true
                OPTIMIZE_ALL=true
                EMBED_ALL=true
                GENRES_ALL=true
                shift 1
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift 1
                ;;
            -y|--yes)
                ASSUME_YES=true
                shift 1
                ;;
            --filter)
                if [[ $# -gt 1 ]] && ! [[ "$2" =~ ^- ]]; then
                    PATCH_FILTER="$2"
                    shift 2
                else
                    echo -e "${RED}❌ Error: --filter requires a search term or playlist.${RESET}"
                    exit 1
                fi
                ;;
            --keep-old)
                KEEP_OLD=true
                shift 1
                ;;
            -o|--optimize|--optimize-all)
                DO_OPTIMIZE=true
                OPTIMIZE_ALL=true
                shift 1
                ;;
            -e|--embed|--embed-all|--revert-optimize|--embed-covers)
                EMBED_ALL=true
                shift 1
                ;;
            -g|--genres|--genres-all)
                GENRES_ALL=true
                shift 1
                ;;
            -l|--lyrics)
                FETCH_LYRICS=true
                shift 1
                ;;
            --synced-only)
                SYNCED_ONLY=true
                shift 1
                ;;
            -t|--threads)
                if [[ $# -lt 2 ]] || ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -le 0 ]; then
                    echo -e "${RED}❌ Error: --threads requires a positive integer.${RESET}"
                    exit 1
                fi
                THREADS="$2"
                shift 2
                ;;
            -f|--fallback|--fallback-only)
                FALLBACK_ONLY=true
                shift 1
                if [[ $# -gt 0 ]] && [[ "$1" =~ ^https://open\.spotify\.com/ ]]; then
                    RAW_URL="$1"
                    shift 1
                fi
                ;;
            --split)
                SPLIT_MODE=true
                if [[ $# -gt 1 ]] && ! [[ "$2" =~ ^- ]]; then
                    SPLIT_FILE="$2"
                    shift 2
                else
                    shift 1
                fi
                ;;
            --cue)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --cue requires a file path.${RESET}"
                    exit 1
                fi
                CUE_FILE="$2"
                shift 2
                ;;
            --tracklist)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --tracklist requires a file path.${RESET}"
                    exit 1
                fi
                TRACKLIST_FILE="$2"
                shift 2
                ;;
            --audit-duration|--audit)
                AUDIT_DURATION_MODE=true
                shift 1
                ;;
            --embed-lyrics)
                EMBED_LYRICS_MODE=true
                shift 1
                ;;
            --search)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    echo -e "${RED}❌ Error: --search requires a search query.${RESET}"
                    exit 1
                fi
                SEARCH_QUERY="$2"
                shift 2
                ;;
            --allow-live)
                ALLOW_LIVE=true
                shift 1
                ;;
            --allow-remix)
                ALLOW_REMIX=true
                shift 1
                ;;
            https://open.spotify.com/*)
                RAW_URL="$1"
                shift 1
                ;;
            *)
                if [ "$PATCH_MODE" = true ] && [ -z "$PATCH_FILTER" ]; then
                    PATCH_FILTER="$1"
                    shift 1
                elif [ "$DELETE_PLAYLIST_MODE" = true ] && [ -z "$DELETE_PLAYLIST_TARGET" ]; then
                    DELETE_PLAYLIST_TARGET="$1"
                    shift 1
                elif [ "$ROMAJI_MODE" = true ] && [ -z "$ROMAJI_TARGET" ]; then
                    ROMAJI_TARGET="$1"
                    shift 1
                elif [ "$SPLIT_MODE" = true ] && [ -z "$SPLIT_FILE" ]; then
                    SPLIT_FILE="$1"
                    shift 1
                elif [ -z "$RAW_URL" ] && [ -z "$SEARCH_QUERY" ]; then
                    SEARCH_QUERY="$1"
                    shift 1
                else
                    echo -e "${RED}❌ Error: Unrecognized argument: $1${RESET}"
                    echo "Run '$0 --help' for usage instructions."
                    exit 1
                fi
                ;;
        esac
    done

    # Immediate return for update or uninstall
    if [ "$UPDATE_MODE" = true ] || [ "$UNINSTALL_MODE" = true ]; then
        return 0
    fi

    # Resolve cross-compatible playlist target
    if [ -n "$PLAYLIST_NAME" ]; then
        if [ "$PATCH_MODE" = true ] && [ -z "$PATCH_FILTER" ]; then
            PATCH_FILTER="$PLAYLIST_NAME"
        elif [ "$DELETE_PLAYLIST_MODE" = true ] && [ -z "$DELETE_PLAYLIST_TARGET" ]; then
            DELETE_PLAYLIST_TARGET="$PLAYLIST_NAME"
        elif [ "$ROMAJI_MODE" = true ] && [ -z "$ROMAJI_TARGET" ]; then
            ROMAJI_TARGET="$PLAYLIST_NAME"
        elif [ "$PATCH_MODE" = false ] && [ "$DELETE_PLAYLIST_MODE" = false ] && [ "$ROMAJI_MODE" = false ] && [ -z "$RAW_URL" ]; then
            PLAYLIST_MANAGER_MODE=true
        fi
    fi

    # Clean Spotify URL if provided
    if [ -n "$RAW_URL" ]; then
        CLEAN_URL=$(echo "$RAW_URL" | grep -oE 'https://open\.spotify\.com/(playlist|album|track)/[a-zA-Z0-9]+' | head -n 1)
        if [ -z "$CLEAN_URL" ]; then
            echo -e "${RED}❌ Error: Invalid Spotify URL.${RESET}"
            exit 1
        fi
    fi

    # Format validation
    if [ "$PATCH_MODE" = true ]; then
        validate_format "$PATCH_FORMAT"
    else
        validate_format "$AUDIO_FORMAT"
    fi

    # Action validation
    if [ "$PLAYLIST_MANAGER_MODE" = false ] && [ "$MERGE_PLAYLIST_MODE" = false ] && \
       [ "$DELETE_PLAYLIST_MODE" = false ] && [ "$PATCH_MODE" = false ] && [ "$ROMAJI_MODE" = false ] && \
       [ "$OPTIMIZE_ALL" = false ] && [ "$EMBED_ALL" = false ] && \
       [ "$GENRES_ALL" = false ] && [ "$FETCH_LYRICS" = false ] && [ "$FALLBACK_ONLY" = false ] && \
       [ "$DEDUP_MODE" = false ] && [ "$FIX_TAGS_MODE" = false ] && [ "$STATUS_MODE" = false ] && \
       [ "$REPAIR_PLAYLISTS_MODE" = false ] && [ "$SPLIT_MODE" = false ] && \
       [ "$AUDIT_DURATION_MODE" = false ] && [ "$EMBED_LYRICS_MODE" = false ] && \
       [ -z "$SEARCH_QUERY" ] && [ -z "$CLEAN_URL" ]; then
        echo -e "${RED}❌ Error: No valid action or URL specified.${RESET}"
        echo ""
        show_help
        exit 1
    fi

    if [ "$FALLBACK_ONLY" = true ] && [ -z "$CLEAN_URL" ] && [ ! -s "erros.spotdl" ]; then
        echo -e "${RED}❌ Error: --fallback requested without URL, but no 'erros.spotdl' file was found.${RESET}"
        exit 1
    fi
}
