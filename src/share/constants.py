"""Shared constants, supported audio formats, and user-configurable settings."""

import os
from .config import get_config_value

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

LOSSLESS_EXTENSIONS = ('.flac', '.wav', '.aiff', '.ape', '.alac')
LOSSY_EXTENSIONS = ('.m4a', '.opus', '.ogg', '.mp3')

# Standard cover art filenames recognized across modules and players
_cfg_covers = get_config_value("cover_filenames")
if _cfg_covers:
    COVER_FILENAMES = tuple(x.strip() for x in _cfg_covers.split(",") if x.strip())
else:
    COVER_FILENAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.jpeg', 'folder.png')

COVER_NAME = get_config_value("cover_name", "cover.jpg") or "cover.jpg"
try:
    COVER_RESOLUTION = int(get_config_value("cover_resolution", "600") or 600)
except (ValueError, TypeError):
    COVER_RESOLUTION = 600

# System, filesystem, and player directories to ignore during library traversal
_cfg_ignored = get_config_value("ignored_dirs")
if _cfg_ignored:
    IGNORED_DIRS = {x.strip().lower() for x in _cfg_ignored.split(",") if x.strip()}
else:
    IGNORED_DIRS = {
        'lost.dir',
        '.trash-1000',
        '.trash',
        'system volume information',
        '.android_secure',
        '.rockbox',
        'backup',
        '__pycache__',
        '.git',
        'playlists',
        'lib',
    }

# Library audit and full-album rip detection thresholds
try:
    AUDIT_THRESHOLD_SECONDS = float(get_config_value("audit_threshold", "600") or 600.0)
except (ValueError, TypeError):
    AUDIT_THRESHOLD_SECONDS = 600.0

try:
    AUDIT_RATIO_THRESHOLD = float(get_config_value("audit_ratio", "1.5") or 1.5)
except (ValueError, TypeError):
    AUDIT_RATIO_THRESHOLD = 1.5

# Network API timeouts and Last.fm scrobbler batching
try:
    API_TIMEOUT = int(get_config_value("api_timeout", "8") or 8)
except (ValueError, TypeError):
    API_TIMEOUT = 8

try:
    SCROBBLER_BATCH_SIZE = min(50, max(1, int(get_config_value("scrobbler_batch_size", "50") or 50)))
except (ValueError, TypeError):
    SCROBBLER_BATCH_SIZE = 50

# Hardware & Tagging standardization
try:
    ID3_VERSION = int(get_config_value("id3_version", "3") or 3)
except (ValueError, TypeError):
    ID3_VERSION = 3

CLEAN_GHOST_FILES = str(get_config_value("clean_ghost_files", "true")).lower() in ("true", "1", "yes")

# Download provider preferences
SPOTDL_AUDIO_PROVIDERS = get_config_value("spotdl_providers", "youtube youtube-music soundcloud bandcamp") or "youtube youtube-music soundcloud bandcamp"
try:
    SPOTDL_MAX_RETRIES = int(get_config_value("spotdl_max_retries", "1") or 1)
except (ValueError, TypeError):
    SPOTDL_MAX_RETRIES = 1
SPOTDL_THROTTLED_RATE = get_config_value("spotdl_throttled_rate", "100K") or "100K"

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
