#!/usr/bin/env python3
# ==============================================================================
# Module: lib/lyrics.py
# Purpose: Multithreaded missing lyrics scanner (.lrc) via LRCLIB and syncedlyrics
# ==============================================================================

import sys
import os
import json
import urllib.request
import urllib.parse
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import mutagen

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

lock = threading.Lock()
downloaded_count = 0
not_found_count = 0


def fetch_lyrics(artist, title, album, duration, out_path, synced_only=False):
    # 1. LRCLIB GET
    params = {'artist_name': artist, 'track_name': title}
    if album:
        params['album_name'] = album
    if duration:
        params['duration'] = round(duration)

    try:
        url = 'https://lrclib.net/api/get?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'User-Agent': 'MusicLyricsFetcher/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            synced = data.get('syncedLyrics')
            plain = data.get('plainLyrics')
            if synced:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(synced.strip() + '\n')
                return 'synced'
            elif not synced_only and plain:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(plain.strip() + '\n')
                return 'plain'
    except Exception:
        pass

    # 2. LRCLIB SEARCH
    try:
        q = f"{artist} {title}"
        url_search = 'https://lrclib.net/api/search?' + urllib.parse.urlencode({'q': q})
        req_search = urllib.request.Request(url_search, headers={'User-Agent': 'MusicLyricsFetcher/1.0'})
        with urllib.request.urlopen(req_search, timeout=5) as resp:
            results = json.loads(resp.read().decode('utf-8'))
            for r in results:
                synced = r.get('syncedLyrics')
                if synced:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(synced.strip() + '\n')
                    return 'synced'
            if not synced_only:
                for r in results:
                    plain = r.get('plainLyrics')
                    if plain:
                        with open(out_path, 'w', encoding='utf-8') as f:
                            f.write(plain.strip() + '\n')
                        return 'plain'
    except Exception:
        pass

    # 3. syncedlyrics CLI fallback
    try:
        cmd = ['syncedlyrics', f"{artist} - {title}", '-o', out_path]
        if synced_only:
            cmd.append('--synced-only')
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return 'synced'
    except Exception:
        pass

    return None


def get_audio_info(audio_path):
    artist, title, album, duration = "", "", "", None
    try:
        m = mutagen.File(audio_path)
        if m:
            if hasattr(m, 'info') and m.info:
                duration = getattr(m.info, 'length', None)
            if m.tags:
                artist = m.tags.get('artist', [''])[0] if isinstance(m.tags.get('artist'), list) else str(m.tags.get('artist') or '')
                title = m.tags.get('title', [''])[0] if isinstance(m.tags.get('title'), list) else str(m.tags.get('title') or '')
                album = m.tags.get('album', [''])[0] if isinstance(m.tags.get('album'), list) else str(m.tags.get('album') or '')
    except Exception:
        pass

    if not title or not artist:
        base = os.path.splitext(os.path.basename(audio_path))[0]
        if ' - ' in base:
            parts = base.split(' - ')
            artist = parts[-1].strip()
            title = ' - '.join(parts[:-1]).strip()
            if ' ' in title and title.split(' ')[0].isdigit():
                title = ' '.join(title.split(' ')[1:]).strip()

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
