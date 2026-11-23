#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/cli.sh
# Purpose: CLI help presentation, command grammar, and argument parsing
# ==============================================================================

show_help() {
    cat << EOF
Usage: syncdap <resource> [action] [target] [options]

Rockbox and Digital Audio Player (DAP) music library synchronization manager.

Resources:
  download <URL>   Download track, album, or playlist from Spotify
  search <query>   Search track or album by name via metadata APIs
  rescue [target]  Stream recovery via fallback downloader
  library          Library-wide operations (status, audit, dedup, optimize, patch, fix, romaji)
  artist           Artist-scoped operations (status, audit, dedup, fix, romaji, patch)
  album            Album-scoped operations (status, audit, dedup, expand, optimize, patch, fix, romaji)
  track            Track-scoped operations (status, audit, expand, patch, romaji)
  playlist         M3U/M3U8 playlist management, repair, and cleanup
  covers           Album artwork extraction and tag embedding
  lyrics           Synchronized LRC lyrics maintenance and embedding
  tags             Audio metadata standardization and transliteration
  scrobbler        Last.fm Rockbox scrobble synchronization (sync, auth, status, logout)
  status           Display library health and statistics (alias to library status)
  config           Inspect or modify persistent configuration
  update           Update syncdap to latest git commit
  uninstall        Completely remove syncdap from system

Options:
  -c, --config <path>   Use custom configuration file
  -r, --root-dir <path> Target music library or DAP mount root (default: .)
  -t, --threads <num>   Worker thread concurrency (default: 4)
  -F, --format <fmt>    Audio format: flac, mp3, m4a, opus, ogg, wav
  -n, --dry-run         Simulate execution without modifying files
  -y, --yes             Skip interactive confirmation prompts
  -v, --verbose         Show detailed execution diagnostics on stderr
  -q, --quiet           Suppress non-error status output
  --json                Output machine-readable JSON array or object
  --plain               Output headerless tab-separated plain text
  --icons / --no-icons  Force enable or disable Nerd Font symbols
  -V, --version         Print version information
  -h, --help            Print help information
EOF
}

show_resource_help() {
    local res="${1:-}"
    case "$res" in
        library)
            cat << EOF
Usage: syncdap library <action> [options]

Library-wide maintenance and optimization utilities.

Actions:
  status      Display library health, statistics, and storage dashboard
  audit       Audit library tracks >10m against metadata APIs
  dedup       Deduplicate tracks keeping highest audio quality
  optimize    Execute complete Rockbox/DAP library optimization pipeline
  patch [fmt] Transcode or upgrade entire library to target format
  fix         Unify ALBUM/ALBUMARTIST tags and clean ghost files
  romaji      Transliterate Japanese tags and paths across library

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -n, --dry-run         Simulate execution without modifying files
  -v, --verbose         Show detailed execution diagnostics
  --json                Output results as JSON (status, audit)
  --plain               Output results as plain text (status)
EOF
            ;;
        artist)
            cat << EOF
Usage: syncdap artist <action> <artist> [options]

Artist-scoped maintenance and inspection utilities.

Actions:
  status <artist>      Display artist track count, formats, and health
  audit <artist>       Audit artist tracks >10m against metadata APIs
  dedup <artist>       Deduplicate tracks within this artist folder
  fix <artist>         Standardize artist metadata and ALBUMARTIST tags
  romaji <artist>      Transliterate Japanese tags for this artist
  patch [fmt] <artist> Transcode artist tracks to target format

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -n, --dry-run         Simulate execution without modifying files
  -v, --verbose         Show detailed execution diagnostics
EOF
            ;;
        album)
            cat << EOF
Usage: syncdap album <action> [album_dir] [options]

Album-scoped maintenance, unbundling, and inspection utilities.

Actions:
  status [album]       Display album statistics and track health
  audit [album]        Audit album tracks >10m against metadata APIs
  dedup [album]        Deduplicate tracks within this album
  expand [file]        Unbundle full-album single-file rip into individual tracks
  optimize [album]     Optimize album for Rockbox (covers + tags + dedup)
  fix [album]          Standardize album metadata and ALBUMARTIST tags
  romaji [album]       Transliterate Japanese tags for this album
  patch [fmt] [album]  Transcode album tracks to target format

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -F, --format <fmt>    Target audio format for re-downloaded tracks
  -n, --dry-run         Simulate execution without modifying files
  --json                Output audit results as machine-readable JSON
EOF
            ;;
        track)
            cat << EOF
Usage: syncdap track <action> <file> [options]

Single-track inspection and maintenance utilities.

Actions:
  status <file>       Inspect single track metadata, format, bitrate, and lyrics
  audit <file>        Check if track duration exceeds API duration (>1.5x)
  expand <file>       Expand single-file album rip into tagged tracks
  romaji <file>       Transliterate Japanese metadata in track tags and .lrc
  patch [fmt] <file>  Transcode single track to target audio format

Options:
  -F, --format <fmt>  Target audio format for re-downloaded or transcoded track
  -n, --dry-run       Simulate execution without modifying files
  --json              Output track status as JSON
EOF
            ;;
        covers)
            cat << EOF
Usage: syncdap covers <action> [options]

Album artwork extraction and tag embedding.

Actions:
  optimize    Extract cover.jpg and strip embedded art (Rockbox DAP mode)
  embed       Embed cover.jpg from album directory into audio tags

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -n, --dry-run         Simulate execution without modifying files
  -v, --verbose         Show detailed execution diagnostics
EOF
            ;;
        lyrics)
            cat << EOF
Usage: syncdap lyrics <action> [options]

Synchronized LRC lyrics maintenance and metadata embedding.

Actions:
  fetch       Scan and download missing timestamped .lrc lyrics
  embed       Embed lyrics directly into audio metadata tags

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  --synced-only         Accept only timestamped [mm:ss] lyrics
  -t, --threads <num>   Worker thread concurrency (default: 4)
  -n, --dry-run         Simulate execution without modifying files
EOF
            ;;
        playlist)
            cat << EOF
Usage: syncdap playlist <action> [options]

M3U/M3U8 playlist creation, maintenance, and repair.

Actions:
  manage [name]          Interactive terminal playlist manager
  merge <p1> <p2> [out]  Merge two playlists and deduplicate shared tracks
  delete <name>          Delete playlist file and optionally purge tracks
  repair                 Relink moved or renamed audio files in playlists

Options:
  -r, --root-dir <path>  Target music library or DAP mount root
  -n, --dry-run          Simulate execution without modifying files
  -y, --yes              Skip interactive confirmation prompts
EOF
            ;;
        tags)
            cat << EOF
Usage: syncdap tags <action> [options]

Audio metadata standardization and transliteration.

Actions:
  fix              Unify ALBUM/ALBUMARTIST tags and clean ghost files
  genres           Enrich missing genre tags via multi-API fallback
  romaji [target]  Transliterate Japanese tags and paths to Romaji

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -n, --dry-run         Simulate execution without modifying files
  -v, --verbose         Show detailed execution diagnostics
EOF
            ;;
        config)
            cat << EOF
Usage: syncdap config [action] [options]

Inspect or modify persistent syncdap configuration.

Actions:
  <key>=<value>    Set configuration value (e.g. syncdap config icons=true)
  set <key> <val>  Set a configuration key and value
  get <key>        Retrieve a configuration value
  list             Display current configuration values
  init             Initialize default configuration file
EOF
            ;;
        status)
            cat << EOF
Usage: syncdap status [options]

Display library health and statistics dashboard (alias to 'syncdap library status').

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  --json                Output machine-readable JSON dashboard
  --plain               Output tab-separated plain text summary
EOF
            ;;
        scrobbler)
            cat << EOF
Usage: syncdap scrobbler [action] [target] [options]

Last.fm Rockbox scrobble synchronization and account management.

Actions:
  sync [path]   Parse .scrobbler.log, submit batches of 50, and rotate log (default)
  auth          Execute Last.fm desktop browser authentication
  status [path] Display session validity, watermark, and pending scrobbles
  logout        Revoke local Last.fm session credentials

Options:
  -r, --root-dir <path> Target music library or DAP mount root (default: .)
  --tz-offset <hours>   Explicit UTC offset (e.g. -3) when log reports #TZ/UNKNOWN
  --keep-log            Retain .scrobbler.log on DAP after upload
  -n, --dry-run         Simulate execution without modifying files or submitting
  -y, --yes             Skip confirmation prompts during authentication
  -v, --verbose         Show detailed execution diagnostics
  -q, --quiet           Suppress non-error status output
  --json                Output machine-readable JSON
  --plain               Output headerless tab-separated plain text
EOF
            ;;
        download)
            cat << EOF
Usage: syncdap [download] <URL> [options]

Ingest track, album, or playlist from Spotify.

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -F, --format <fmt>    Audio format: flac, mp3, m4a, opus, ogg, wav
  -t, --threads <num>   Worker thread concurrency (default: 4)
  --synced-only         Accept only timestamped synchronized lyrics
EOF
            ;;
        search)
            cat << EOF
Usage: syncdap search <query> [options]

Search track or album by name via metadata APIs and download.

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -F, --format <fmt>    Audio format: flac, mp3, m4a, opus, ogg, wav
  --json                Output search metadata as JSON without downloading
EOF
            ;;
        rescue)
            cat << EOF
Usage: syncdap rescue [target] [options]

Stream recovery via fallback downloader (or retry erros.spotdl).

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -F, --format <fmt>    Audio format: flac, mp3, m4a, opus, ogg, wav
  -t, --threads <num>   Worker thread concurrency (default: 4)
EOF
            ;;
        patch)
            cat << EOF
Usage: syncdap patch [format] [target] [options]

Transcode or upgrade tracks to target audio format.

Options:
  -r, --root-dir <path> Target music library or DAP mount root
  -t, --threads <num>   Worker thread concurrency (default: 4)
  --keep-old            Retain original files alongside converted files
  -n, --dry-run         Simulate execution without modifying files
  -y, --yes             Skip interactive confirmation prompts
EOF
            ;;
        *)
            show_help
            ;;
    esac
}

show_version() {
    echo "syncdap ${SYNCDAP_VERSION:-2.0.0}"
}

# Subcommand state variables
SUBCOMMAND=""
SUBACTION=""
COMMAND_ARGS=()
OUTPUT_FORMAT="table"
TZ_OFFSET=""
KEEP_LOG=false
AUTH_FLAG=false

parse_arguments() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    local raw_positionals=()
    local help_requested=false

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                help_requested=true
                shift 1
                ;;
            -V|--version)
                show_version
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift 1
                ;;
            -q|--quiet)
                QUIET=true
                shift 1
                ;;
            -n|--dry-run|-d)
                DRY_RUN=true
                shift 1
                ;;
            -y|--yes)
                ASSUME_YES=true
                shift 1
                ;;
            --keep-old)
                KEEP_OLD=true
                shift 1
                ;;
            --keep-log)
                KEEP_LOG=true
                shift 1
                ;;
            --auth)
                AUTH_FLAG=true
                shift 1
                ;;
            --tz-offset|--timezone)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^-?[a-zA-Z] ]]; then
                    error_dual "Missing timezone offset" "$1 requires hours (e.g. -3 or 2)" "" "" "Pass a valid offset: syncdap scrobbler $1 -3"
                    exit 2
                fi
                TZ_OFFSET="$2"
                shift 2
                ;;
            --synced-only)
                SYNCED_ONLY=true
                shift 1
                ;;
            --json)
                OUTPUT_FORMAT="json"
                shift 1
                ;;
            --plain)
                OUTPUT_FORMAT="plain"
                shift 1
                ;;
            --icons)
                FORCE_ICONS="true"
                init_iconography
                shift 1
                ;;
            --no-icons)
                FORCE_ICONS="false"
                init_iconography
                shift 1
                ;;
            -F|--format)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    error_dual "Missing format argument" "-F / --format requires an audio format" "" "" "Specify flac, mp3, m4a, opus, ogg, or wav"
                    exit 2
                fi
                validate_format "$2"
                AUDIO_FORMAT="$2"
                shift 2
                ;;
            -r|--root-dir)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    error_dual "Missing directory path" "-r / --root-dir requires a directory path" "" "" "Pass a valid directory path: syncdap -r /mnt/dap"
                    exit 2
                fi
                TARGET_ROOT="$2"
                shift 2
                ;;
            -t|--threads)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    error_dual "Missing thread count" "-t / --threads requires a number" "" "" "Specify thread count: syncdap -t 4"
                    exit 2
                fi
                THREADS="$2"
                shift 2
                ;;
            -c|--config)
                if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                    error_dual "Missing config path" "-c / --config requires a configuration file" "" "" "Pass a path: syncdap -c ~/.config/syncdap/config"
                    exit 2
                fi
                CONFIG_FILE="$2"
                load_config
                shift 2
                ;;
            -*)
                error_dual "Unrecognized option '$1'" "The specified option is not supported" "$1" "" "Run 'syncdap --help' for available options."
                exit 2
                ;;
            *)
                raw_positionals+=("$1")
                shift 1
                ;;
        esac
    done

    # Handle help request if triggered
    if [ "$help_requested" = true ]; then
        if [ ${#raw_positionals[@]} -gt 0 ]; then
            show_resource_help "${raw_positionals[0]}"
        else
            show_help
        fi
        exit 0
    fi

    if [ ${#raw_positionals[@]} -eq 0 ]; then
        show_help
        exit 0
    fi

    local first="${raw_positionals[0]}"

    # Support 'syncdap help <resource>' syntax
    if [ "$first" = "help" ]; then
        if [ ${#raw_positionals[@]} -gt 1 ]; then
            show_resource_help "${raw_positionals[1]}"
        else
            show_help
        fi
        exit 0
    fi

    # Automatic detection for Spotify URL
    if [[ "$first" =~ ^https://open\.spotify\.com/ ]] || [[ "$first" =~ ^spotify: ]]; then
        SUBCOMMAND="download"
        RAW_URL="$first"
        return 0
    fi

    SUBCOMMAND="$first"

    # Route hierarchical resources
    case "$SUBCOMMAND" in
        library|artist|album|track|covers|lyrics|playlist|tags)
            if [ ${#raw_positionals[@]} -lt 2 ]; then
                error_dual "Missing action for '$SUBCOMMAND'" "Resource requires a specific action" "syncdap $SUBCOMMAND" "" "Run 'syncdap $SUBCOMMAND --help' to view available actions."
                exit 2
            fi
            SUBACTION="${raw_positionals[1]}"
            if [ ${#raw_positionals[@]} -gt 2 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:2}")
            fi

            # Validate actions per resource
            case "$SUBCOMMAND" in
                library)
                    if [[ ! "$SUBACTION" =~ ^(status|audit|dedup|optimize|patch|fix|romaji)$ ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'library'" "Supported actions: status, audit, dedup, optimize, patch, fix, romaji" "syncdap library $SUBACTION" "" "Run 'syncdap library --help' for available actions."
                        exit 2
                    fi
                    ;;
                artist)
                    if [[ ! "$SUBACTION" =~ ^(status|audit|dedup|fix|romaji|patch)$ ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'artist'" "Supported actions: status, audit, dedup, fix, romaji, patch" "syncdap artist $SUBACTION" "" "Run 'syncdap artist --help' for available actions."
                        exit 2
                    fi
                    if [ ${#COMMAND_ARGS[@]} -eq 0 ]; then
                        error_dual "Missing artist target" "Artist-scoped commands require an artist name or directory" "syncdap artist $SUBACTION <artist>" "" "Example: syncdap artist $SUBACTION 'Queen'"
                        exit 2
                    fi
                    ;;
                album)
                    if [[ ! "$SUBACTION" =~ ^(status|audit|dedup|expand|optimize|patch|fix|romaji)$ ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'album'" "Supported actions: status, audit, dedup, expand, optimize, patch, fix, romaji" "syncdap album $SUBACTION" "" "Run 'syncdap album --help' for available actions."
                        exit 2
                    fi
                    ;;
                track)
                    if [[ ! "$SUBACTION" =~ ^(status|audit|expand|patch|romaji)$ ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'track'" "Supported actions: status, audit, expand, patch, romaji" "syncdap track $SUBACTION" "" "Run 'syncdap track --help' for available actions."
                        exit 2
                    fi
                    if [ ${#COMMAND_ARGS[@]} -eq 0 ]; then
                        error_dual "Missing audio file target" "Track-scoped commands require an audio file path" "syncdap track $SUBACTION <file>" "" "Example: syncdap track $SUBACTION 'song.flac'"
                        exit 2
                    fi
                    ;;
                covers)
                    if [[ "$SUBACTION" != "optimize" && "$SUBACTION" != "embed" ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'covers'" "Supported actions: optimize, embed" "syncdap covers $SUBACTION" "" "Run 'syncdap covers --help' for available actions."
                        exit 2
                    fi
                    ;;
                lyrics)
                    if [[ "$SUBACTION" != "fetch" && "$SUBACTION" != "embed" ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'lyrics'" "Supported actions: fetch, embed" "syncdap lyrics $SUBACTION" "" "Run 'syncdap lyrics --help' for available actions."
                        exit 2
                    fi
                    ;;
                playlist)
                    if [[ "$SUBACTION" != "manage" && "$SUBACTION" != "merge" && "$SUBACTION" != "delete" && "$SUBACTION" != "repair" ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'playlist'" "Supported actions: manage, merge, delete, repair" "syncdap playlist $SUBACTION" "" "Run 'syncdap playlist --help' for available actions."
                        exit 2
                    fi
                    ;;
                tags)
                    if [[ "$SUBACTION" != "fix" && "$SUBACTION" != "genres" && "$SUBACTION" != "romaji" ]]; then
                        error_dual "Invalid action '$SUBACTION' for 'tags'" "Supported actions: fix, genres, romaji" "syncdap tags $SUBACTION" "" "Run 'syncdap tags --help' for available actions."
                        exit 2
                    fi
                    ;;
            esac
            ;;
        config)
            if [ ${#raw_positionals[@]} -gt 1 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:1}")
            fi
            ;;
        scrobbler)
            if [ "$AUTH_FLAG" = true ]; then
                SUBACTION="auth"
                if [ ${#raw_positionals[@]} -gt 1 ]; then
                    COMMAND_ARGS=("${raw_positionals[@]:1}")
                fi
            elif [ ${#raw_positionals[@]} -ge 2 ]; then
                local cand="${raw_positionals[1]}"
                if [[ "$cand" =~ ^(sync|auth|status|logout)$ ]]; then
                    SUBACTION="$cand"
                    if [ ${#raw_positionals[@]} -gt 2 ]; then
                        COMMAND_ARGS=("${raw_positionals[@]:2}")
                    fi
                else
                    SUBACTION="sync"
                    COMMAND_ARGS=("${raw_positionals[@]:1}")
                fi
            else
                SUBACTION="sync"
            fi
            ;;
        download|search|rescue|patch|update|uninstall)
            if [ ${#raw_positionals[@]} -gt 1 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:1}")
            fi
            ;;
        status)
            # Route 'syncdap status' as 'syncdap library status'
            SUBCOMMAND="library"
            SUBACTION="status"
            if [ ${#raw_positionals[@]} -gt 1 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:1}")
            fi
            ;;
        dedup)
            # Route 'syncdap dedup' as 'syncdap library dedup'
            SUBCOMMAND="library"
            SUBACTION="dedup"
            if [ ${#raw_positionals[@]} -gt 1 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:1}")
            fi
            ;;
        optimize)
            # Route 'syncdap optimize' as 'syncdap library optimize'
            SUBCOMMAND="library"
            SUBACTION="optimize"
            if [ ${#raw_positionals[@]} -gt 1 ]; then
                COMMAND_ARGS=("${raw_positionals[@]:1}")
            fi
            ;;
        *)
            if [[ "$first" =~ ^https?:// ]]; then
                SUBCOMMAND="download"
                RAW_URL="$first"
            else
                error_dual "Unrecognized command '$first'" "The command does not exist in syncdap" "$first" "" "Run 'syncdap --help' for usage instructions."
                exit 2
            fi
            ;;
    esac
}
