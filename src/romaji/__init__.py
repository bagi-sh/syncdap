# ==============================================================================
# Package: src/romaji
# Purpose: Japanese music metadata and FAT32 path transliteration
# ==============================================================================

from .translit import (
    to_romaji,
    contains_japanese,
    capitalize_romaji_title,
    sanitize_filename,
    is_kanji,
    is_hiragana,
    AUDIO_EXTENSIONS,
)
from .tags import process_audio_tags
from .lyrics import process_lrc_file
from .playlist import resolve_playlist_track, collect_files_from_playlist, process_playlist_file
from .engine import run_romaji_transliteration, rename_file_or_dir
from .cli import main

__all__ = [
    "to_romaji",
    "contains_japanese",
    "capitalize_romaji_title",
    "sanitize_filename",
    "is_kanji",
    "is_hiragana",
    "AUDIO_EXTENSIONS",
    "process_audio_tags",
    "process_lrc_file",
    "resolve_playlist_track",
    "collect_files_from_playlist",
    "process_playlist_file",
    "rename_file_or_dir",
    "run_romaji_transliteration",
    "main",
]
