# ==============================================================================
# Package: src/share
# Purpose: Shared utilities, constants, normalization, and helper functions
# ==============================================================================

from .constants import (
    AUDIO_EXTENSIONS,
    LOSSLESS_EXTENSIONS,
    LOSSY_EXTENSIONS,
    IGNORED_DIRS,
    FULL_ALBUM_PATTERNS,
    LIVE_PATTERNS,
    REMIX_PATTERNS,
)
from .text import (
    SYMBOL_REPLACEMENTS,
    normalize_str,
    clean_string,
    clean_term,
    sanitize_filename,
    parse_filename_metadata,
    parse_timestamp_to_seconds,
)
from .lyrics import fetch_lyrics, embed_lyrics_into_file
from .audio import (
    find_audio_files,
    get_audio_metadata,
    has_embedded_cover_fast,
    get_file_duration,
    is_lossless,
    get_bitrate_kbps,
    track_number_from_filename,
    audio_quality_wins,
    is_valid_audio,
)
from .playlists import (
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
    expand_playlist_entries,
)
from .api import (
    normalize_album_name,
    get_track_duration,
    get_album_tracklist,
    itunes_search,
    itunes_song_metadata,
)

__all__ = [
    # constants
    "AUDIO_EXTENSIONS",
    "LOSSLESS_EXTENSIONS",
    "LOSSY_EXTENSIONS",
    "IGNORED_DIRS",
    "FULL_ALBUM_PATTERNS",
    "LIVE_PATTERNS",
    "REMIX_PATTERNS",
    # text
    "SYMBOL_REPLACEMENTS",
    "normalize_str",
    "clean_string",
    "clean_term",
    "sanitize_filename",
    "parse_filename_metadata",
    "parse_timestamp_to_seconds",
    # lyrics
    "fetch_lyrics",
    "embed_lyrics_into_file",
    # audio
    "find_audio_files",
    "get_audio_metadata",
    "has_embedded_cover_fast",
    "get_file_duration",
    "is_lossless",
    "get_bitrate_kbps",
    "track_number_from_filename",
    "audio_quality_wins",
    "is_valid_audio",
    # playlists
    "get_default_playlist_dir",
    "find_playlist_file",
    "get_all_playlist_files",
    "resolve_track_file",
    "format_track_for_playlist",
    "expand_playlist_entries",
    # api
    "normalize_album_name",
    "get_track_duration",
    "get_album_tracklist",
    "itunes_search",
    "itunes_song_metadata",
]
