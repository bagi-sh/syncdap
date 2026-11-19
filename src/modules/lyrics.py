#!/usr/bin/env python3
# ==============================================================================
# Module: src/lyrics.py
# Purpose: Multithreaded missing lyrics scanner (.lrc) via LRCLIB and syncedlyrics
# ==============================================================================

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from share import AUDIO_EXTENSIONS, fetch_lyrics, embed_lyrics_into_file, read_audio_metadata

lock = threading.Lock()
downloaded_count = 0
embedded_count = 0
not_found_count = 0


def process_item(idx, total, item, synced_only, do_embed):
    global downloaded_count, embedded_count, not_found_count
    audio_path, lrc_path = item

    meta = read_audio_metadata(audio_path)
    artist = meta.get('artist', '')
    title = meta.get('title', '')
    album = meta.get('album', '')
    duration = meta.get('duration') or 0.0
    lrc_content = None

    if os.path.isfile(lrc_path):
        try:
            with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
                lrc_content = f.read()
        except Exception:
            pass

    if not lrc_content:
        status = fetch_lyrics(artist, title, album, duration, lrc_path, synced_only)
        if status and os.path.isfile(lrc_path):
            with lock:
                downloaded_count += 1
            try:
                with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lrc_content = f.read()
            except Exception:
                pass
        else:
            with lock:
                not_found_count += 1
                print(f"   [{idx}/{total}] ⚠️ Not found: {artist} - {title}")
            return

    embed_info = ""
    if do_embed and lrc_content:
        if embed_lyrics_into_file(audio_path, lrc_content):
            with lock:
                embedded_count += 1
            embed_info = " [embedded in tags]"

    with lock:
        print(f"   [{idx}/{total}] ✅ {artist} - {title}{embed_info}")


def main():
    if len(sys.argv) < 2:
        print("Usage: lyrics.py <dirs_file> [threads] [synced_only] [--embed]")
        sys.exit(1)

    dirs_file = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    synced_only = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False
    do_embed = '--embed' in sys.argv or (len(sys.argv) > 4 and sys.argv[4].lower() == 'true')

    target_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            target_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    candidate_tracks = []
    for d in target_dirs:
        for fname in os.listdir(d):
            if fname.lower().endswith(AUDIO_EXTENSIONS):
                audio_path = os.path.join(d, fname)
                lrc_path = os.path.splitext(audio_path)[0] + '.lrc'
                # If embedding, include tracks with existing .lrc too
                if do_embed or not os.path.exists(lrc_path):
                    candidate_tracks.append((audio_path, lrc_path))

    total = len(candidate_tracks)
    if total == 0:
        action = "already have embedded lyrics" if do_embed else "already have .lrc lyrics"
        print(f"   ✨ All inspected tracks {action}.")
        sys.exit(0)

    mode_label = "Scanning and embedding lyrics into metadata" if do_embed else "Searching missing lyrics"
    print(f"   {mode_label} for {total} track(s) with {threads} worker(s)...")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_item, i + 1, total, item, synced_only, do_embed)
                   for i, item in enumerate(candidate_tracks)]
        for f in futures:
            f.result()

    summary = f"\n   📊 Lyrics processing completed: {downloaded_count} downloaded, {embedded_count} embedded, {not_found_count} missing out of {total}."
    print(summary)


if __name__ == '__main__':
    main()
