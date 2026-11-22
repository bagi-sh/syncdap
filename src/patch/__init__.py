"""Audio format patching and transcoding package."""

from .metadata import extract_metadata_from_file, transfer_tags_to_file
from .playlist import update_playlists, handle_playlist_patch
from .worker import upgrade_track
from .cli import main

__all__ = [
    "extract_metadata_from_file",
    "transfer_tags_to_file",
    "update_playlists",
    "handle_playlist_patch",
    "upgrade_track",
    "main",
]
