"""Shared constants, supported audio formats, and user-configurable settings."""

import os
from .config import get_config_value, resolve_setting

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

LOSSLESS_EXTENSIONS = ('.flac', '.wav', '.aiff', '.ape', '.alac')
LOSSY_EXTENSIONS = ('.m4a', '.opus', '.ogg', '.mp3')

# Standard cover art filenames recognized across modules and players
_raw_covers = resolve_setting(
    env_vars=["SYNCDAP_CLI_COVER_FILENAMES", "SYNCDAP_COVER_FILENAMES"],
    config_keys=["cover_filenames", "cover-filenames"],
    default="cover.jpg,cover.jpeg,cover.png,folder.jpg,folder.jpeg,folder.png",
    val_type=str,
)
COVER_FILENAMES = tuple(x.strip() for x in _raw_covers.split(",") if x.strip())

COVER_NAME = resolve_setting(
    env_vars=["SYNCDAP_CLI_COVER_NAME", "SYNCDAP_COVER_NAME"],
    config_keys=["cover_name", "cover-name"],
    default="cover.jpg",
    val_type=str,
)

COVER_RESOLUTION = resolve_setting(
    env_vars=["SYNCDAP_CLI_COVER_RESOLUTION", "SYNCDAP_COVER_RESOLUTION"],
    config_keys=["cover_resolution", "cover-resolution"],
    default=600,
    val_type=int,
)

# System, filesystem, and player directories to ignore during library traversal
_raw_ignored = resolve_setting(
    env_vars=["SYNCDAP_CLI_IGNORED_DIRS", "SYNCDAP_IGNORED_DIRS"],
    config_keys=["ignored_dirs", "ignored-dirs"],
    default="lost.dir,.trash-1000,.trash,system volume information,.android_secure,.rockbox,backup,__pycache__,.git,playlists,lib",
    val_type=str,
)
IGNORED_DIRS = {x.strip().lower() for x in _raw_ignored.split(",") if x.strip()}

# Library audit and full-album rip detection thresholds
AUDIT_THRESHOLD_SECONDS = resolve_setting(
    env_vars=["SYNCDAP_CLI_AUDIT_THRESHOLD", "SYNCDAP_AUDIT_THRESHOLD"],
    config_keys=["audit_threshold", "audit-threshold"],
    default=600.0,
    val_type=float,
)

AUDIT_RATIO_THRESHOLD = resolve_setting(
    env_vars=["SYNCDAP_CLI_AUDIT_RATIO", "SYNCDAP_AUDIT_RATIO"],
    config_keys=["audit_ratio", "audit-ratio"],
    default=1.5,
    val_type=float,
)

# Network API timeouts and Last.fm scrobbler batching
API_TIMEOUT = resolve_setting(
    env_vars=["SYNCDAP_CLI_API_TIMEOUT", "SYNCDAP_API_TIMEOUT"],
    config_keys=["api_timeout", "api-timeout"],
    default=8,
    val_type=int,
)

SCROBBLER_BATCH_SIZE = min(
    50,
    max(
        1,
        resolve_setting(
            env_vars=["SYNCDAP_CLI_SCROBBLER_BATCH_SIZE", "SYNCDAP_SCROBBLER_BATCH_SIZE"],
            config_keys=["scrobbler_batch_size", "scrobbler-batch-size"],
            default=50,
            val_type=int,
        ),
    ),
)

# Hardware & Tagging standardization
ID3_VERSION = resolve_setting(
    env_vars=["SYNCDAP_CLI_ID3_VERSION", "SYNCDAP_ID3_VERSION"],
    config_keys=["id3_version", "id3-version"],
    default=3,
    val_type=int,
)

CLEAN_GHOST_FILES = resolve_setting(
    env_vars=["SYNCDAP_CLI_CLEAN_GHOST_FILES", "SYNCDAP_CLEAN_GHOST_FILES"],
    config_keys=["clean_ghost_files", "clean-ghost-files"],
    default=True,
    val_type=bool,
)

# Download provider preferences
SPOTDL_AUDIO_PROVIDERS = resolve_setting(
    env_vars=["SYNCDAP_CLI_SPOTDL_PROVIDERS", "SYNCDAP_SPOTDL_PROVIDERS"],
    config_keys=["spotdl_providers", "spotdl-providers"],
    default="youtube youtube-music soundcloud bandcamp",
    val_type=str,
)

SPOTDL_MAX_RETRIES = resolve_setting(
    env_vars=["SYNCDAP_CLI_SPOTDL_MAX_RETRIES", "SYNCDAP_SPOTDL_MAX_RETRIES"],
    config_keys=["spotdl_max_retries", "spotdl-max-retries"],
    default=1,
    val_type=int,
)

SPOTDL_THROTTLED_RATE = resolve_setting(
    env_vars=["SYNCDAP_CLI_SPOTDL_THROTTLED_RATE", "SYNCDAP_SPOTDL_THROTTLED_RATE"],
    config_keys=["spotdl_throttled_rate", "spotdl-throttled-rate"],
    default="100K",
    val_type=str,
)

# Regex patterns for download filtering and candidate ranking
FULL_ALBUM_PATTERNS = [
    r'\b(full[\s\-_]*album)\b',
    r'\b(album[\s\-_]*completo)\b',
    r'\b(álbum[\s\-_]*completo)\b',
    r'\b(complete[\s\-_]*album)\b',
    r'\b(discography)\b',
    r'\b(discografia)\b',
    r'\b(full[\s\-_]*ep)\b',
    r'\b(full[\s\-_]*tape)\b',
    r'\b(full[\s\-_]*vinyl)\b',
    r'\b(all\s+tracks)\b',
    r'\b(greatest\s+hits(\s+full)?)\b',
    r'\b(best\s+of(\s+full)?)\b',
]

LIVE_PATTERNS = [
    r'\b(ao[\s\-_]*vivo)\b',
    r'\b(en[\s\-_]*vivo)\b',
    r'\b(live(\s+(at|in|from|version|session|acoustic|tour|concert))?)\b',
    r'\b(in\s+concert)\b',
    r'\b(unplugged)\b',
    r'\b(bootleg)\b',
    r'\b(radio\s+broadcast)\b',
    r'\b(tour\s+\d{4})\b',
]

REMIX_PATTERNS = [
    r'\b(re[\s\-_]*mix(ed)?)\b',
    r'\b(club\s+mix)\b',
    r'\b(extended\s+(mix|version))\b',
    r'\b(slowed(\s+(and|\+)\s+reverb)?)\b',
    r'\b(sped[\s\-_]*up)\b',
    r'\b(speed[\s\-_]*up)\b',
    r'\b(nightcore)\b',
    r'\b(daycore)\b',
    r'\b(bass[\s\-_]*boost(ed)?)\b',
    r'\b(instrumental)\b',
    r'\b(karaoke)\b',
    r'\b(cover)\b',
    r'\b(tribute)\b',
    r'\b(parody)\b',
    r'\b(edit)\b',
    r'\b(mashup)\b',
    r'\b(8d\s+audio)\b',
]

# Last.fm Scrobbler API Credentials and Configuration
DEFAULT_LASTFM_API_KEY = "968d453baa45e579a864cb6f9cb145ef"
DEFAULT_LASTFM_API_SECRET = "a6253b76b199de52509870c4881cd2db"

LASTFM_API_KEY = os.getenv("SYNCDAP_LASTFM_API_KEY", DEFAULT_LASTFM_API_KEY)
LASTFM_API_SECRET = os.getenv("SYNCDAP_LASTFM_API_SECRET", DEFAULT_LASTFM_API_SECRET)
