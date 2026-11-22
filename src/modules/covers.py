#!/usr/bin/env python3
"""Cover art management module.

Handles universal artwork embedding into audio containers and Rockbox optimization
(extracting external cover.jpg and stripping embedded images to save RAM and disk space).
"""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from share import AUDIO_EXTENSIONS
from share.covers import (
    find_cover_image,
    extract_cover_from_file,
    embed_cover_in_file,
    has_embedded_cover,
    strip_covers_from_file,
)
from share.icons import ICONS

lock = threading.Lock()
processed_albums = 0
updated_tracks = 0
already_optimized_albums = 0


def process_embed_album(idx, total, album_dir):
    global processed_albums, updated_tracks

    audio_files = [
        os.path.join(album_dir, f)
        for f in os.listdir(album_dir)
        if f.lower().endswith(AUDIO_EXTENSIONS)
    ]
    if not audio_files:
        return

    cover_file = find_cover_image(album_dir)

    # If no cover file on disk, try extracting from any track
    if not cover_file:
        cover_out = os.path.join(album_dir, 'cover.jpg')
        for f in audio_files:
            if extract_cover_from_file(f, cover_out):
                cover_file = cover_out
                break

    if not cover_file:
        with lock:
            print(f"   [{idx}/{total}] {ICONS.warn} No cover found for: {album_dir}")
        return

    mime_type = "image/png" if cover_file.lower().endswith('.png') else "image/jpeg"
    try:
        with open(cover_file, 'rb') as cf:
            img_data = cf.read()
    except Exception:
        return

    if not img_data:
        return

    album_updated = 0
    for f in audio_files:
        if embed_cover_in_file(f, img_data, mime_type):
            album_updated += 1

    with lock:
        processed_albums += 1
        updated_tracks += album_updated
        print(f"   [{idx}/{total}] {ICONS.img} {album_dir} ({album_updated}/{len(audio_files)} tracks embedded)")


def process_optimize_album(idx, total, album_dir):
    global processed_albums, updated_tracks, already_optimized_albums

    audio_files = [
        os.path.join(album_dir, f)
        for f in os.listdir(album_dir)
        if f.lower().endswith(AUDIO_EXTENSIONS)
        and os.path.isfile(os.path.join(album_dir, f))
        and os.path.getsize(os.path.join(album_dir, f)) > 0
    ]
    if not audio_files:
        return

    cover_file = find_cover_image(album_dir)

    # Check which tracks currently have embedded artwork
    tracks_with_embeds = [f for f in audio_files if has_embedded_cover(f)]

    # If the album already has cover.jpg and no track has embeds, it is ALREADY optimized!
    if cover_file and not tracks_with_embeds:
        with lock:
            already_optimized_albums += 1
        return

    # If no cover on disk, extract from tracks that still have embeds
    if not cover_file:
        cover_out = os.path.join(album_dir, 'cover.jpg')
        for f in (tracks_with_embeds or audio_files):
            if extract_cover_from_file(f, cover_out):
                cover_file = cover_out
                break

    album_stripped = 0
    for f in tracks_with_embeds:
        if strip_covers_from_file(f):
            album_stripped += 1

    with lock:
        processed_albums += 1
        updated_tracks += album_stripped
        print(f"   [{idx}/{total}] {ICONS.ok} {album_dir} ({album_stripped}/{len(audio_files)} tracks stripped)")


def main():
    if len(sys.argv) < 3:
        print("Usage: covers.py <mode:embed|optimize> <dirs_file> [threads]", file=sys.stderr)
        sys.exit(2)

    mode = sys.argv[1].lower()
    dirs_file = sys.argv[2]
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    album_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            album_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    total = len(album_dirs)
    if total == 0:
        print(f"   {ICONS.info} No album folders found to process.")
        sys.exit(0)

    action_label = "Embedding cover arts" if mode == "embed" else "Stripping embedded covers (Rockbox mode)"
    print(f"   {action_label} across {total} album(s) using {threads} worker(s)...")

    worker_fn = process_embed_album if mode == "embed" else process_optimize_album

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(worker_fn, i + 1, total, d) for i, d in enumerate(album_dirs)]
        for f in futures:
            f.result()

    if mode == "optimize":
        print(
            f"\n   {ICONS.ok} Cover art operation completed: {processed_albums} album(s) stripped "
            f"({updated_tracks} tracks), {already_optimized_albums} album(s) were already optimized."
        )
    else:
        print(
            f"\n   {ICONS.ok} Cover art operation completed: {processed_albums} albums processed, "
            f"{updated_tracks} tracks embedded."
        )


if __name__ == '__main__':
    main()
