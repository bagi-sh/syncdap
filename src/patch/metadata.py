"""Audio metadata preservation across transcode formats."""

import os
from share import read_audio_metadata, write_audio_metadata


def extract_metadata_from_file(file_path: str) -> dict:
    """Extract metadata, source URLs, and cover data from an existing audio file."""
    meta = read_audio_metadata(file_path, fallback_to_filename=True)
    meta['tracks_count'] = meta.get('total_tracks', '')
    return meta


def transfer_tags_to_file(dest_file: str, meta: dict, cover_path: str | None = None) -> bool:
    """Write preserved metadata and cover art into the newly downloaded audio file."""
    img_data = meta.get('cover_data')
    mime_type = meta.get('cover_mime', 'image/jpeg')
    if not img_data and cover_path and os.path.isfile(cover_path):
        try:
            with open(cover_path, 'rb') as f:
                img_data = f.read()
            mime_type = 'image/png' if cover_path.lower().endswith('.png') else 'image/jpeg'
        except Exception:
            pass

    return write_audio_metadata(
        dest_file,
        title=meta.get('title'),
        artist=meta.get('artist'),
        album=meta.get('album'),
        album_artist=meta.get('album_artist'),
        track_num=meta.get('track_num'),
        total_tracks=meta.get('total_tracks') or meta.get('tracks_count'),
        year=meta.get('year'),
        genre=meta.get('genre'),
        cover_data=img_data,
        cover_mime=mime_type,
    )
