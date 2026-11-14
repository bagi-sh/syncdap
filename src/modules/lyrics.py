#!/usr/bin/env python3
# ==============================================================================
# Module: src/lyrics.py
# Purpose: Multithreaded missing lyrics scanner (.lrc) via LRCLIB and syncedlyrics
# ==============================================================================

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from share import AUDIO_EXTENSIONS, fetch_lyrics, get_audio_metadata

lock = threading.Lock()
downloaded_count = 0
not_found_count = 0


def get_audio_info(audio_path):
    meta = get_audio_metadata(audio_path)
    artist, title, album, duration = meta['artist'], meta['title'], meta['album'], meta['duration']

    if not title or not artist:
        base = os.path.splitext(os.path.basename(audio_path))[0]
        if ' - ' in base:
            parts = base.split(' - ')
            artist = parts[-1].strip()
            title = ' - '.join(parts[:-1]).strip()
            if ' ' in title and title.split(' ')[0].isdigit():
                title = ' '.join(title.split(' ')[1:]).strip()

    return artist, title, album, duration

    return artist, title, album, duration


def process_item(idx, total, item, synced_only):
    global downloaded_count, not_found_count
    audio_path, lrc_path = item

    artist, title, album, duration = get_audio_info(audio_path)

    status = fetch_lyrics(artist, title, album, duration, lrc_path, synced_only)
    with lock:
        if status:
            downloaded_count += 1
            print(f"   [{idx}/{total}] ✅ {artist} - {title} ({status})")
        else:
            not_found_count += 1
            print(f"   [{idx}/{total}] ⚠️ Not found: {artist} - {title}")


def main():
    if len(sys.argv) < 2:
        print("Usage: lyrics.py <dirs_file> [threads] [synced_only]")
        sys.exit(1)

    dirs_file = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    synced_only = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False

    target_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            target_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    missing_tracks = []
    for d in target_dirs:
        for fname in os.listdir(d):
            if fname.lower().endswith(AUDIO_EXTENSIONS):
                audio_path = os.path.join(d, fname)
                lrc_path = os.path.splitext(audio_path)[0] + '.lrc'
                if not os.path.exists(lrc_path):
                    missing_tracks.append((audio_path, lrc_path))

    total = len(missing_tracks)
    if total == 0:
        print("   ✨ All inspected tracks already have .lrc lyrics.")
        sys.exit(0)

    print(f"   Found {total} track(s) missing lyrics. Searching with {threads} worker(s)...")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_item, i + 1, total, item, synced_only)
                   for i, item in enumerate(missing_tracks)]
        for f in futures:
            f.result()

    print(f"\n   📊 Lyrics search completed: {downloaded_count} saved, {not_found_count} not found out of {total}.")


if __name__ == '__main__':
    main()
