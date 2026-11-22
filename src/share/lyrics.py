"""Shared lyrics format detection and normalization helpers."""

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


def embed_lyrics_into_file(audio_path: str, lrc_text: str) -> bool:
    """
    Embed lyrics (synced or plain text) directly into audio metadata headers.
    Supports MP3 (USLT), FLAC/OGG/OPUS (LYRICS/UNSYNCEDLYRICS), and MP4/M4A (©lyr).
    """
    if not os.path.isfile(audio_path) or not lrc_text or not lrc_text.strip():
        return False

    ext = os.path.splitext(audio_path)[1].lower()
    text = lrc_text.strip()

    try:
        if ext == '.mp3':
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, USLT
            audio = MP3(audio_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall('USLT')
            audio.tags.add(USLT(encoding=3, lang='eng', desc='', text=text))
            audio.save(v2_version=3)
            return True

        elif ext == '.flac':
            from mutagen.flac import FLAC
            audio = FLAC(audio_path)
            audio['lyrics'] = [text]
            audio['unsyncedlyrics'] = [text]
            audio.save()
            return True

        elif ext == '.m4a':
            from mutagen.mp4 import MP4
            audio = MP4(audio_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['\xa9lyr'] = [text]
            audio.save()
            return True

        elif ext in ('.ogg', '.opus'):
            import mutagen
            audio = mutagen.File(audio_path)
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                audio.tags['lyrics'] = [text]
                audio.tags['unsyncedlyrics'] = [text]
                audio.save()
                return True

    except Exception:
        return False

    return False


def is_lrc_synced(lrc_path_or_content: str) -> bool:
    """Check if .lrc file or text contains synced timestamp lines ([mm:ss])."""
    if not lrc_path_or_content:
        return False
    import re
    if os.path.isfile(lrc_path_or_content):
        try:
            with open(lrc_path_or_content, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if re.match(r'^\s*\[\d{2}:\d{2}', line):
                        return True
        except Exception:
            pass
        return False
    for line in lrc_path_or_content.splitlines():
        if re.match(r'^\s*\[\d{2}:\d{2}', line):
            return True
    return False
