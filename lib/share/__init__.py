# ==============================================================================
# Package: lib/share
# Purpose: Shared utilities, constants, normalization, and helper functions
# ==============================================================================

from .constants import (
    AUDIO_EXTENSIONS,
    LOSSLESS_EXTENSIONS,
    LOSSY_EXTENSIONS,
    IGNORED_DIRS,
)
from .text import (
    SYMBOL_REPLACEMENTS,
    normalize_str,
    clean_string,
    clean_term,
    sanitize_filename,
    parse_filename_metadata,
)
from .lyrics import fetch_lyrics
from .audio import (
    find_audio_files,
    get_audio_metadata,
    has_embedded_cover_fast,
)
from .playlists import (
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
)

__all__ = [
    "AUDIO_EXTENSIONS",
    "LOSSLESS_EXTENSIONS",
    "LOSSY_EXTENSIONS",
    "IGNORED_DIRS",
    "SYMBOL_REPLACEMENTS",
    "normalize_str",
    "clean_string",
    "clean_term",
    "sanitize_filename",
    "parse_filename_metadata",
    "fetch_lyrics",
    "find_audio_files",
    "get_audio_metadata",
    "has_embedded_cover_fast",
    "get_default_playlist_dir",
    "find_playlist_file",
    "get_all_playlist_files",
    "resolve_track_file",
    "format_track_for_playlist",
]
