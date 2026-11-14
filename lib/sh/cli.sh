#!/usr/bin/env bash
# ==============================================================================
# Module: lib/sh/cli.sh
# Purpose: CLI help presentation and command-line argument parsing
# ==============================================================================

show_help() {
    cat << 'EOF'
Usage:
  syncdap [OPTIONS] <SPOTIFY_URL>
  syncdap [COMMAND] [OPTIONS]

Primary Commands & Modes:
  <URL>                        Download album, playlist, or track from Spotify.
  -p, --patch [FMT] [TARGET]   Patch library tracks or playlist to FORMAT (default: flac).
                               Target can be a playlist name (.m3u8), artist, album, or all.
                               Alias: -u, --upgrade
  -R, --romaji [TARGET]        Transliterate Japanese Kanji/Kana to Romaji (Hepburn) & sanitize
                               FAT32 paths for Rockbox DAPs. Target: playlist, path, or --all.
                               Alias: --transliterate, --rockbox-romaji
  -P, --playlist [NAME]        Interactive playlist manager (create, edit, merge, delete).
                               When passed with an argument to other commands, sets target playlist.
  -D, --delete [PLAYLIST]      Delete a playlist and its audio files from disk.
                               Alias: --delete-playlist
  -M, --merge PL1 PL2 [OUT]    Merge two playlists into one, deduplicating shared tracks.
                               Alias: --merge-playlists
  -e, --embed                  Embed album cover art (cover.jpg) into all audio files.
                               Alias: --embed-all, --embed-covers, --revert-optimize
  -o, --optimize               Optimize for Rockbox/DAP: deduplicate library, strip embedded covers
                               (skipping already optimized), sanitize tags, and repair/clean playlists.
                               When used standalone: optimizes library. When used with URL: optimizes download.
                               Alias: --optimize-all
  --dedup                      Deduplicate audio files keeping highest quality (FLAC > M4A > MP3)
                               and synchronize playlist references.
  --fix-tags, --metadata       Audit and repair tags for Rockbox (unify ALBUM/ALBUMARTIST, remove 0-byte).
  --repair-playlists           Audit and repair playlists (relink renamed tracks, prune truly missing).
  -g, --genres                 Enrich genre metadata album-by-album (iTunes -> Deezer -> MusicBrainz).
                               Alias: --genres-all
  -l, --lyrics                 Scan and download missing .lrc lyrics for audio tracks.
  -s, --status, --stats        Display comprehensive music library statistics & health dashboard.
  -f, --fallback [URL]         Direct yt-dlp rescue with metadata, cover art, and lyrics.
                               If no URL is given: rescues failed tracks from 'erros.spotdl'.
                               Alias: --fallback-only

Universal & Compatible Options (Work across multiple commands):
  -a, --all                    Apply command to entire music library (romaji, patch, embed, optimize, genres, lyrics).
  -d, --dry-run                Simulate actions without modifying files on disk (romaji, patch, delete).
  -y, --yes                    Assume yes to all prompts / automated non-interactive mode (patch, delete, merge).
  -F, --format FORMAT          Audio format: flac, mp3, m4a, opus, ogg, wav (download, patch, fallback).
  -P, --playlist NAME          Target specific playlist for --patch, --romaji, --delete, or --lyrics.
  -r, --root-dir DIR           Root library / player directory (e.g. /run/media/bagi/F695-0800 or .).
  -t, --threads NUM            Concurrency level for downloads and processing (default: 4).
  --keep-old                   In patch mode, keep original files alongside new files.
  --synced-only                In lyrics search, accept only timestamped synced lyrics ([mm:ss]).
  -h, --help                   Display this help message and exit.

Examples:
  syncdap "https://open.spotify.com/album/..."
  syncdap -F flac "https://open.spotify.com/album/..."
  syncdap --patch flac "citypop (WIP)"
  syncdap -p flac -d
  syncdap -R --all
  syncdap -R -P "Osu.m3u8" -r /run/media/bagi/F695-0800 -d
  syncdap -P
  syncdap --delete "citypop (WIP)" -y
  syncdap --merge "pl1" "pl2" "merged_pl"
  syncdap --embed
  syncdap --optimize
  syncdap --genres
  syncdap --lyrics --synced-only
  syncdap --fallback
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
                else
                    echo -e "${RED}❌ Error: Unrecognized argument: $1${RESET}"
                    echo "Run '$0 --help' for usage instructions."
                    exit 1
                fi
                ;;
        esac
    done

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
       [ "$REPAIR_PLAYLISTS_MODE" = false ] && [ -z "$CLEAN_URL" ]; then
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
