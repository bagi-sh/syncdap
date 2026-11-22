#!/usr/bin/env python3
"""Album-level genre enrichment module.

Queries online APIs (iTunes, Deezer, MusicBrainz) to resolve canonical genres
for albums and writes standardized genre tags across audio formats.
"""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from share import (
    AUDIO_EXTENSIONS,
    read_audio_metadata,
    set_audio_genre,
    resolve_online_genre,
)
from share.icons import ICONS

print_lock = threading.Lock()
updated_albums = 0
already_set_albums = 0
not_found_albums = 0
total_tracks_updated = 0


def process_album(idx, total, album_dir):
    global updated_albums, already_set_albums, not_found_albums, total_tracks_updated

    audio_files = [
        os.path.join(album_dir, f)
        for f in os.listdir(album_dir)
        if f.lower().endswith(AUDIO_EXTENSIONS)
    ]
    if not audio_files:
        return

    clean_path = os.path.normpath(album_dir)
    parts = clean_path.split(os.sep)
    folder_artist = parts[-2] if len(parts) >= 2 and parts[-2] != '.' else ""
    folder_album = parts[-1] if len(parts) >= 1 else ""

    existing_genre = None
    tracks_to_update = []

    for f in audio_files:
        meta = read_audio_metadata(f)
        g = meta.get('genre')
        if g:
            if not existing_genre:
                existing_genre = g
        else:
            tracks_to_update.append(f)

    if not tracks_to_update:
        with print_lock:
            already_set_albums += 1
        return

    resolved_genre = existing_genre
    source = "Existing Track"

    if not resolved_genre:
        artist = folder_artist
        album = folder_album

        if not artist or not album:
            meta0 = read_audio_metadata(audio_files[0])
            artist = artist or meta0.get('artist', '')
            album = album or meta0.get('album', '')

        resolved_genre, source = resolve_online_genre(artist, album)

    if not resolved_genre:
        with print_lock:
            not_found_albums += 1
            print(f"   [{idx}/{total}] {ICONS.warn} Genre not found for album: {folder_artist} / {folder_album}")
        return

    applied_count = 0
    for f in tracks_to_update:
        if set_audio_genre(f, resolved_genre):
            applied_count += 1

    with print_lock:
        updated_albums += 1
        total_tracks_updated += applied_count
        print(
            f"   [{idx}/{total}] {ICONS.tag} {resolved_genre} [{source}] -> "
            f"{folder_artist} / {folder_album} ({applied_count}/{len(audio_files)} tracks updated)"
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: genres.py <dirs_file> [threads]", file=sys.stderr)
        sys.exit(2)

    dirs_file = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    album_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            album_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    total = len(album_dirs)
    if total == 0:
        print(f"   {ICONS.info} No album folders found to inspect for genre.")
        sys.exit(0)

    max_workers = min(threads, 4)
    print(f"   Processing {total} album(s) with {max_workers} worker(s) using multi-API fallbacks (iTunes -> Deezer -> MusicBrainz)...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_album, i + 1, total, d) for i, d in enumerate(album_dirs)]
        for f in futures:
            f.result()

    print(
        f"\n   {ICONS.ok} Genre metadata completed: {updated_albums} album(s) updated ({total_tracks_updated} tracks), "
        f"{already_set_albums} album(s) already complete, {not_found_albums} not found out of {total}."
    )


if __name__ == '__main__':
    main()
