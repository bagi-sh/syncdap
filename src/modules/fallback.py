#!/usr/bin/env python3
# ==============================================================================
# Module: src/fallback.py
# Purpose: Parallel fallback rescue via yt-dlp + universal metadata & cover embedding
# ==============================================================================

import sys
import os
import json
import uuid
import shutil
import urllib.request
import urllib.parse
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, TCON, APIC, COMM
from mutagen.mp4 import MP4, MP4Cover

from share import (
    fetch_lyrics,
    sanitize_filename,
    FULL_ALBUM_PATTERNS,
    LIVE_PATTERNS,
    REMIX_PATTERNS,
)

lock = threading.Lock()


def score_video_candidate(cand: dict, artist: str, title: str, expected_dur: float | None = None,
                          allow_live: bool = False, allow_remix: bool = False) -> int:
    """Score a search candidate to filter out full albums, unwanted live tracks, and remixes."""
    c_title = (cand.get('title') or '').lower()
    channel = (cand.get('channel') or cand.get('uploader') or '').lower()
    dur = cand.get('duration') or 0
    t_clean = title.lower()

    q_has_live = bool(re.search(r'\b(live|ao[\s\-_]*vivo|en[\s\-_]*vivo)\b', t_clean)) or allow_live
    q_has_remix = bool(re.search(r'\b(re[\s\-_]*mix|club\s+mix|edit)\b', t_clean)) or allow_remix

    score = 100

    # 1. Full album rejection (hard penalty)
    for pat in FULL_ALBUM_PATTERNS:
        if re.search(pat, c_title):
            return -999

    # 2. Duration check against expected length
    if expected_dur and expected_dur > 0:
        if dur > 1.4 * expected_dur:
            return -999
        if dur < 0.6 * expected_dur:
            score -= 80
        else:
            diff = abs(dur - expected_dur)
            if diff <= 5:
                score += 35
            elif diff <= 15:
                score += 20
    elif dur > 720:  # If duration unknown but exceeds 12 minutes, penalize heavily
        score -= 150

    # 3. Live version filter
    if not q_has_live:
        for pat in LIVE_PATTERNS:
            if re.search(pat, c_title):
                score -= 80
                break

    # 4. Remix / bootleg / karaoke filter
    if not q_has_remix:
        for pat in REMIX_PATTERNS:
            if re.search(pat, c_title):
                score -= 80
                break

    # 5. Channel affinity & Topic channel boost
    art_clean = artist.lower()
    if channel.endswith(' - topic'):
        score += 60
    elif art_clean in channel or channel in art_clean:
        score += 40

    if cand.get('channel_is_verified'):
        score += 15

    return score


def find_best_candidate_url(artist: str, title: str, expected_dur: float | None,
                            js_args: list[str], allow_live: bool = False,
                            allow_remix: bool = False) -> str:
    """Query top 5 candidates via yt-dlp and return the highest-scoring candidate URL."""
    search_query = f"ytsearch5:{artist} - {title}"
    cmd = ['yt-dlp', '--flat-playlist', '--dump-json', *js_args, search_query]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        candidates = []
        for line in proc.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except Exception:
                    pass

        if candidates:
            scored = [(score_video_candidate(c, artist, title, expected_dur, allow_live, allow_remix), c)
                      for c in candidates]
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, best_cand = scored[0]
            cand_url = best_cand.get('url') or best_cand.get('webpage_url')
            if best_score > 0 and cand_url:
                return cand_url
    except Exception:
        pass

    return f"ytsearch1:{artist} - {title}"


def sanitize(name):
    return sanitize_filename(name)


def tag_audio_file(file_path, artist, album, title, track_num, tracks_count, year, genre, cover_jpg):
    ext = os.path.splitext(file_path)[1].lower()
    img_data = None
    mime_type = "image/jpeg"
    if cover_jpg and os.path.isfile(cover_jpg):
        try:
            with open(cover_jpg, 'rb') as cf:
                img_data = cf.read()
            if cover_jpg.lower().endswith('.png'):
                mime_type = "image/png"
        except Exception:
            pass

    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall('TIT2')
            audio.tags.delall('TPE1')
            audio.tags.delall('TALB')
            audio.tags.delall('TRCK')
            audio.tags.delall('TDRC')
            audio.tags.delall('TCON')

            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TALB(encoding=3, text=album))
            trck_str = f"{track_num}/{tracks_count}" if tracks_count else str(track_num)
            audio.tags.add(TRCK(encoding=3, text=trck_str))
            if year:
                audio.tags.add(TDRC(encoding=3, text=str(year)))
            if genre:
                audio.tags.add(TCON(encoding=3, text=str(genre)))
            if img_data:
                audio.tags.delall('APIC')
                audio.tags.add(APIC(encoding=3, mime=mime_type, type=3, desc='', data=img_data))
            audio.save(v2_version=3)

        elif ext == '.flac':
            audio = FLAC(file_path)
            audio['title'] = [title]
            audio['artist'] = [artist]
            audio['album'] = [album]
            audio['tracknumber'] = [str(track_num)]
            if tracks_count:
                audio['totaltracks'] = [str(tracks_count)]
            if year:
                audio['date'] = [str(year)]
            if genre:
                audio['genre'] = [str(genre)]
            if img_data:
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3
                pic.mime = mime_type
                pic.desc = ''
                pic.data = img_data
                audio.add_picture(pic)
            audio.save()

        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['\xa9nam'] = [title]
            audio.tags['\xa9ART'] = [artist]
            audio.tags['\xa9alb'] = [album]
            t_num = int(track_num) if str(track_num).isdigit() else 1
            t_tot = int(tracks_count) if str(tracks_count).isdigit() else 0
            audio.tags['trkn'] = [(t_num, t_tot)]
            if year:
                audio.tags['\xa9day'] = [str(year)]
            if genre:
                audio.tags['\xa9gen'] = [str(genre)]
            if img_data:
                cov_format = MP4Cover.FORMAT_PNG if 'png' in mime_type else MP4Cover.FORMAT_JPEG
                audio.tags['covr'] = [MP4Cover(img_data, imageformat=cov_format)]
            audio.save()

    except Exception:
        pass


def rescue_track(idx, total, d, temp_dir, target_m3u, target_ext, js_args, synced_only):
    artist = sanitize(d.get('artist') or 'Unknown Artist')
    album = sanitize(d.get('album_name') or 'Unknown Album')
    title = sanitize(d.get('name') or 'Untitled')

    try:
        track_num = f"{int(d.get('track_number')):02d}"
    except (ValueError, TypeError):
        track_num = "01"

    try:
        tracks_count = str(int(d.get('tracks_count')))
    except (ValueError, TypeError):
        tracks_count = ""

    try:
        year = str(int(d.get('year')))
    except (ValueError, TypeError):
        year = ""

    duration = d.get('duration')
    cover_url = str(d.get('cover_url') or '').strip()
    genres = d.get('genres') or []
    genre = str(genres[0]).title() if genres else ""

    album_dir = os.path.join(artist, album)
    final_audio = os.path.join(album_dir, f"{track_num} {title} - {artist}.{target_ext}")
    final_lrc = os.path.join(album_dir, f"{track_num} {title} - {artist}.lrc")
    cover_jpg = os.path.join(album_dir, 'cover.jpg')

    os.makedirs(album_dir, exist_ok=True)

    if os.path.exists(final_audio):
        with lock:
            print(f"   [{idx}/{total}] ⏩ Already exists: {final_audio}")
        if not os.path.exists(final_lrc):
            fetch_lyrics(artist, title, album, duration, final_lrc, synced_only)
        if target_m3u and os.path.exists(target_m3u):
            pl_dir = os.path.dirname(os.path.abspath(target_m3u))
            rel_entry = f"{os.path.relpath(os.path.abspath(final_audio), pl_dir)}\n"
            with lock:
                with open(target_m3u, 'r', encoding='utf-8', errors='ignore') as pf:
                    content = pf.read()
                if rel_entry.strip() not in content:
                    with open(target_m3u, 'a', encoding='utf-8') as pf:
                        pf.write(rel_entry)
        return True

    with lock:
        print(f"   [{idx}/{total}] 🔍 Rescuing: {artist} - {title}")

    temp_base = os.path.join(temp_dir, f"rescue_{uuid.uuid4().hex}")
    temp_dest = f"{temp_base}.{target_ext}"

    ytdlp_fmt = 'vorbis' if target_ext == 'ogg' else target_ext
    target_source = find_best_candidate_url(artist, title, duration, js_args)
    cmd = [
        'yt-dlp',
        target_source,
        '--no-playlist',
        *js_args,
        '-x', '--audio-format', ytdlp_fmt,
        '--audio-quality', '0',
        '-o', f"{temp_base}.%(ext)s"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(temp_dest) and os.path.getsize(temp_dest) > 0:
        if not os.path.exists(cover_jpg) and cover_url:
            try:
                urllib.request.urlretrieve(cover_url, cover_jpg)
            except Exception:
                pass

        tag_audio_file(temp_dest, artist, album, title, track_num, tracks_count, year, genre, cover_jpg)
        shutil.move(temp_dest, final_audio)

        lrc_ok = fetch_lyrics(artist, title, album, duration, final_lrc, synced_only)
        lrc_status = "with lyrics" if lrc_ok else "no lyrics found"

        if target_m3u and os.path.exists(target_m3u):
            pl_dir = os.path.dirname(os.path.abspath(target_m3u))
            rel_entry = f"{os.path.relpath(os.path.abspath(final_audio), pl_dir)}\n"
            with lock:
                with open(target_m3u, 'r', encoding='utf-8', errors='ignore') as pf:
                    content = pf.read()
                if rel_entry.strip() not in content:
                    with open(target_m3u, 'a', encoding='utf-8') as pf:
                        pf.write(rel_entry)

        with lock:
            print(f"   [{idx}/{total}] ✅ Saved: {final_audio} ({lrc_status})")
        return True
    else:
        with lock:
            print(f"   [{idx}/{total}] ❌ Could not retrieve audio for: {artist} - {title}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: fallback.py <batch_meta_file> <temp_dir> [target_m3u] [threads] [synced_only] [format] [js_args]")
        sys.exit(1)

    batch_meta_file = sys.argv[1]
    temp_dir = sys.argv[2]
    target_m3u = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    threads = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    synced_only = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False
    target_ext = sys.argv[6].lower() if len(sys.argv) > 6 and sys.argv[6] else "mp3"
    ytdlp_js_raw = sys.argv[7] if len(sys.argv) > 7 else ""

    js_args = ytdlp_js_raw.split() if ytdlp_js_raw else []

    try:
        with open(batch_meta_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"   ❌ Failed to parse metadata file: {e}")
        sys.exit(0)

    tracks = []
    seen_urls = set()
    for d in data:
        if not isinstance(d, dict):
            continue
        url = d.get('url') or ''
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        tracks.append(d)

    total = len(tracks)
    print(f"   Recovering {total} track(s) in {target_ext.upper()} using {threads} parallel worker(s)...")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(rescue_track, i + 1, total, tr, temp_dir, target_m3u, target_ext, js_args, synced_only)
                   for i, tr in enumerate(tracks)]
        for f in futures:
            f.result()


if __name__ == '__main__':
    main()
