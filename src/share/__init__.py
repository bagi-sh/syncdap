"""Shared utilities, constants, normalization, and helper functions."""

from .constants import (
    AUDIO_EXTENSIONS,
    LOSSLESS_EXTENSIONS,
    LOSSY_EXTENSIONS,
    COVER_FILENAMES,
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
    format_duration,
    format_bytes,
)
from .lyrics import (
    fetch_lyrics,
    embed_lyrics_into_file,
    is_lrc_synced,
)
from .covers import (
    find_cover_image,
    extract_cover_from_file,
    embed_cover_in_file,
    has_embedded_cover,
    strip_covers_from_file,
)
from .audio import (
    find_audio_files,
    read_audio_metadata,
    get_audio_metadata,
    write_audio_metadata,
    set_audio_genre,
    has_embedded_cover_fast,
    get_file_duration,
    is_lossless,
    get_bitrate_kbps,
    track_number_from_filename,
    get_audio_quality_score,
    audio_quality_wins,
    is_valid_audio,
)
from .playlists import (
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    clean_playlist_entry,
    resolve_track_file,
    format_track_for_playlist,
    parse_playlist_file,
    patch_playlist_file,
    update_all_playlists,
    expand_playlist_entries,
)
from .api import (
    normalize_album_name,
    get_track_duration,
    get_album_tracklist,
    itunes_search,
    itunes_song_metadata,
    itunes_genre,
    deezer_genre,
    musicbrainz_genre,
    resolve_online_genre,
)
from .config import (
    load_config,
    get_config_value,
)
from .icons import (
    ICONS,
    get_icons,
    format_error_dual,
)

__all__ = [
    # constants
    "AUDIO_EXTENSIONS",
    "LOSSLESS_EXTENSIONS",
    "LOSSY_EXTENSIONS",
    "COVER_FILENAMES",
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
    "format_duration",
    "format_bytes",
    # lyrics
    "fetch_lyrics",
    "embed_lyrics_into_file",
    "is_lrc_synced",
    # covers
    "find_cover_image",
    "extract_cover_from_file",
    "embed_cover_in_file",
    "has_embedded_cover",
    "strip_covers_from_file",
    # audio
    "find_audio_files",
    "read_audio_metadata",
    "get_audio_metadata",
    "write_audio_metadata",
    "set_audio_genre",
    "has_embedded_cover_fast",
    "get_file_duration",
    "is_lossless",
    "get_bitrate_kbps",
    "track_number_from_filename",
    "get_audio_quality_score",
    "audio_quality_wins",
    "is_valid_audio",
    # playlists
    "get_default_playlist_dir",
    "find_playlist_file",
    "get_all_playlist_files",
    "clean_playlist_entry",
    "resolve_track_file",
    "format_track_for_playlist",
    "parse_playlist_file",
    "patch_playlist_file",
    "update_all_playlists",
    "expand_playlist_entries",
    # api
    "normalize_album_name",
    "get_track_duration",
    "get_album_tracklist",
    "itunes_search",
    "itunes_song_metadata",
    "itunes_genre",
    "deezer_genre",
    "musicbrainz_genre",
    "resolve_online_genre",
    # config
    "load_config",
    "get_config_value",
    # icons
    "ICONS",
    "get_icons",
    "format_error_dual",
]
