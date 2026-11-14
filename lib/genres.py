#!/usr/bin/env python3
# ==============================================================================
# Module: lib/genres.py
# Purpose: Album-level multi-API genre enrichment (iTunes -> Deezer -> MusicBrainz)
# ==============================================================================

import sys
import os
import re
import time
import json
import urllib.request
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TCON
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

from share import AUDIO_EXTENSIONS, clean_term

album_genre_cache = {}
artist_genre_cache = {}
cache_lock = threading.Lock()
print_lock = threading.Lock()
updated_albums = 0
already_set_albums = 0
not_found_albums = 0
total_tracks_updated = 0


def itunes_genre(artist, album):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    ca = clean_term(artist)
    calb = clean_term(album)

    # 1. Album search
    if ca and calb:
        try:
            q = f"{ca} {calb}".strip()
            url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
                "term": q,
                "entity": "album",
                "limit": 1
            })
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8', errors='ignore'))
                res = data.get("results", [])
                if res and res[0].get("primaryGenreName"):
                    return res[0]["primaryGenreName"]
        except Exception:
            pass

    # 2. Artist search
    if ca:
        try:
            url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
                "term": ca,
                "entity": "musicArtist",
                "limit": 1
            })
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8', errors='ignore'))
                res = data.get("results", [])
                if res and res[0].get("primaryGenreName"):
                    return res[0]["primaryGenreName"]
        except Exception:
            pass

    return None


def deezer_genre(artist, album):
    headers = {'User-Agent': 'Mozilla/5.0'}
    ca = clean_term(artist)
    calb = clean_term(album)

    # 1. Album search
    if ca and calb:
        try:
            q = f"{ca} {calb}".strip()
            url = "https://api.deezer.com/search/album?" + urllib.parse.urlencode({"q": q, "limit": 1})
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8', errors='ignore'))
                res = data.get("data", [])
                if res:
                    alb_id = res[0].get("id")
                    if alb_id:
                        req2 = urllib.request.Request(f"https://api.deezer.com/album/{alb_id}", headers=headers)
                        with urllib.request.urlopen(req2, timeout=5) as r2:
                            d2 = json.loads(r2.read().decode('utf-8', errors='ignore'))
                            genres = d2.get("genres", {}).get("data", [])
                            if genres and genres[0].get("name"):
                                return genres[0]["name"]
        except Exception:
            pass

    # 2. Artist album search fallback
    if ca:
        try:
            url = "https://api.deezer.com/search/artist?" + urllib.parse.urlencode({"q": ca, "limit": 1})
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode('utf-8', errors='ignore'))
                res = data.get("data", [])
                if res:
                    art_id = res[0].get("id")
                    if art_id:
                        url2 = f"https://api.deezer.com/artist/{art_id}/albums"
                        req2 = urllib.request.Request(url2, headers=headers)
                        with urllib.request.urlopen(req2, timeout=5) as r2:
                            d2 = json.loads(r2.read().decode('utf-8', errors='ignore'))
                            albs = d2.get("data", [])
                            if albs:
                                first_alb = albs[0].get("id")
                                if first_alb:
                                    url3 = f"https://api.deezer.com/album/{first_alb}"
                                    req3 = urllib.request.Request(url3, headers=headers)
                                    with urllib.request.urlopen(req3, timeout=5) as r3:
                                        d3 = json.loads(r3.read().decode('utf-8', errors='ignore'))
                                        genres = d3.get("genres", {}).get("data", [])
                                        if genres and genres[0].get("name"):
                                            return genres[0]["name"]
        except Exception:
            pass

    return None


def musicbrainz_genre(artist, album):
    headers = {'User-Agent': 'MusicLibraryGenreTagger/1.0 (contact@example.com)'}
    ca = clean_term(artist)
    calb = clean_term(album)

    # 1. Release search
    if ca and calb:
        try:
            q = f'artist:"{ca}" AND release:"{calb}"'
            url = "https://musicbrainz.org/ws/2/release/?query=" + urllib.parse.quote(q) + "&fmt=json&limit=1"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read().decode('utf-8', errors='ignore'))
                rels = d.get("releases", [])
                if rels:
                    tags = rels[0].get("tags", [])
                    genres = rels[0].get("genres", [])
                    all_tags = (genres or []) + (tags or [])
                    if all_tags:
                        best = max(all_tags, key=lambda t: t.get("count", 0))
                        return best.get("name", "").title()
        except Exception:
            pass

    # 2. Artist search
    if ca:
        try:
            url = "https://musicbrainz.org/ws/2/artist/?query=" + urllib.parse.quote(ca) + "&fmt=json&limit=2"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read().decode('utf-8', errors='ignore'))
                arts = d.get("artists", [])
                if arts:
                    genres = arts[0].get("genres", []) or []
                    tags = arts[0].get("tags", []) or []
                    all_tags = genres + tags
                    if all_tags:
                        best = max(all_tags, key=lambda t: t.get("count", 0))
                        return best.get("name", "").title()
        except Exception:
            pass

    return None


def resolve_album_genre(artist, album):
    ca = clean_term(artist)
    calb = clean_term(album)

    with cache_lock:
        if (ca, calb) in album_genre_cache:
            return album_genre_cache[(ca, calb)], "Cache"
        if ca in artist_genre_cache:
            return artist_genre_cache[ca], "ArtistCache"

    # 1. iTunes
    g = itunes_genre(artist, album)
    source = "iTunes"

    # 2. Deezer fallback
    if not g:
        time.sleep(0.04)
        g = deezer_genre(artist, album)
        source = "Deezer"

    # 3. MusicBrainz fallback
    if not g:
        time.sleep(0.04)
        g = musicbrainz_genre(artist, album)
        source = "MusicBrainz"

    if g:
        with cache_lock:
            if ca and calb:
                album_genre_cache[(ca, calb)] = g
            if ca:
                artist_genre_cache[ca] = g
        return g, source

    return None, None


def get_file_genre(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                tcon = audio.tags.get('TCON')
                if tcon and tcon.text:
                    return str(tcon.text[0]).strip()
        elif ext == '.flac':
            audio = FLAC(file_path)
            genres = audio.get('genre', [])
            if genres:
                return str(genres[0]).strip()
        elif ext == '.m4a':
            audio = MP4(file_path)
            genres = audio.tags.get('\xa9gen', []) if audio.tags else []
            if genres:
                return str(genres[0]).strip()
        elif ext in ('.ogg', '.opus'):
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            genres = audio.get('genre', [])
            if genres:
                return str(genres[0]).strip()
    except Exception:
        pass
    return None


def set_file_genre(file_path, genre_name):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall('TCON')
            audio.tags.add(TCON(encoding=3, text=genre_name))
            audio.save(v2_version=3)
            return True
        elif ext == '.flac':
            audio = FLAC(file_path)
            audio['genre'] = [genre_name]
            audio.save()
            return True
        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['\xa9gen'] = [genre_name]
            audio.save()
            return True
        elif ext in ('.ogg', '.opus'):
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            audio['genre'] = [genre_name]
            audio.save()
            return True
    except Exception:
        pass
    return False


def process_album(idx, total, album_dir):
    global updated_albums, already_set_albums, not_found_albums, total_tracks_updated

    audio_files = [os.path.join(album_dir, f) for f in os.listdir(album_dir)
                   if f.lower().endswith(AUDIO_EXTENSIONS)]
    if not audio_files:
        return

    clean_path = os.path.normpath(album_dir)
    parts = clean_path.split(os.sep)
    folder_artist = parts[-2] if len(parts) >= 2 and parts[-2] != '.' else ""
    folder_album = parts[-1] if len(parts) >= 1 else ""

    existing_genre = None
    tracks_to_update = []

    for f in audio_files:
        g = get_file_genre(f)
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
            try:
                m = mutagen.File(audio_files[0])
                if m and m.tags:
                    artist = artist or m.tags.get('artist', [''])[0]
                    album = album or m.tags.get('album', [''])[0]
            except Exception:
                pass

        resolved_genre, source = resolve_album_genre(artist, album)

    if not resolved_genre:
        with print_lock:
            not_found_albums += 1
            print(f"   [{idx}/{total}] ⚠️ Genre not found for album: {folder_artist} / {folder_album}")
        return

    applied_count = 0
    for f in tracks_to_update:
        if set_file_genre(f, resolved_genre):
            applied_count += 1

    with print_lock:
        updated_albums += 1
        total_tracks_updated += applied_count
        print(f"   [{idx}/{total}] 🏷️ {resolved_genre} [{source}] -> {folder_artist} / {folder_album} ({applied_count}/{len(audio_files)} tracks updated)")


def main():
    if len(sys.argv) < 2:
        print("Usage: genres.py <dirs_file> [threads]")
        sys.exit(1)

    dirs_file = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    album_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            album_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    total = len(album_dirs)
    if total == 0:
        print("   ℹ️ No album folders found to inspect for genre.")
        sys.exit(0)

    max_workers = min(threads, 4)
    print(f"   Processing {total} album(s) with {max_workers} worker(s) using multi-API fallbacks (iTunes -> Deezer -> MusicBrainz)...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_album, i + 1, total, d) for i, d in enumerate(album_dirs)]
        for f in futures:
            f.result()

    print(f"\n   📊 Genre metadata completed: {updated_albums} album(s) updated ({total_tracks_updated} tracks), {already_set_albums} album(s) already complete, {not_found_albums} not found out of {total}.")


if __name__ == '__main__':
    main()
