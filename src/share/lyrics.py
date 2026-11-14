# ==============================================================================
# Module: src/share/lyrics.py
# Purpose: Shared LRCLIB and syncedlyrics query engine
# ==============================================================================

import json
import os
import subprocess
import urllib.parse
import urllib.request


def fetch_lyrics(artist: str, title: str, album: str = "", duration: float | None = None, out_path: str = "", synced_only: bool = False):
    """
    Fetch lyrics for track from LRCLIB with fallback to syncedlyrics CLI.
    Returns 'synced' or 'plain' on success (both truthy in Python), or None on failure.
    """
    if not artist or not title or not out_path:
        return None

    # 1. LRCLIB GET (exact query)
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

    # 2. LRCLIB SEARCH (fuzzy query)
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
