#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/split.py
# Purpose: Precision lossless album splitter using chapters, CUE sheets,
#          tracklist timestamps, or online metadata (iTunes/MusicBrainz fallback)
# ==============================================================================

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from share import (
    AUDIO_EXTENSIONS,
    clean_string,
    get_audio_metadata,
    parse_timestamp_to_seconds,
    sanitize_filename,
)


# ==============================================================================
# 1. Chapter / CUE / Tracklist parsers
# ==============================================================================

def extract_chapters_from_file(file_path: str) -> list[dict]:
    """Extract embedded chapter markers via ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_chapters',
        file_path
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        chapters = data.get('chapters', [])
        tracks = []
        for i, ch in enumerate(chapters, 1):
            start = float(ch.get('start_time', 0.0))
            end = float(ch.get('end_time', 0.0))
            tags = ch.get('tags', {})
            title = tags.get('title') or f"Track {i:02d}"
            tracks.append({'track_num': i, 'title': title, 'start': start, 'end': end})
        return tracks
    except Exception:
        return []


def parse_cue_file(cue_path: str, total_duration: float | None = None) -> list[dict]:
    """Parse a .cue sheet into track segments with frame-accurate timestamps."""
    if not os.path.isfile(cue_path):
        return []

    tracks = []
    current_track = None

    try:
        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            m_track = re.match(r'^TRACK\s+(\d+)\s+AUDIO', line, re.IGNORECASE)
            if m_track:
                if current_track:
                    tracks.append(current_track)
                current_track = {
                    'track_num': int(m_track.group(1)),
                    'title': f"Track {int(m_track.group(1)):02d}",
                    'start': 0.0,
                    'end': None
                }
                continue

            if current_track:
                m_title = re.match(r'^TITLE\s+[\'"]?(.*?)[\'"]?$', line, re.IGNORECASE)
                if m_title:
                    current_track['title'] = m_title.group(1).strip()
                    continue

                m_performer = re.match(r'^PERFORMER\s+[\'"]?(.*?)[\'"]?$', line, re.IGNORECASE)
                if m_performer:
                    current_track['artist'] = m_performer.group(1).strip()
                    continue

                # INDEX 01 mm:ss:ff  (75 frames/sec in CUE spec)
                m_index = re.match(r'^INDEX\s+01\s+(\d+):(\d+):(\d+)', line, re.IGNORECASE)
                if m_index:
                    mm, ss, ff = int(m_index.group(1)), int(m_index.group(2)), int(m_index.group(3))
                    current_track['start'] = mm * 60.0 + ss + (ff / 75.0)

        if current_track:
            tracks.append(current_track)

        # Fill in end timestamps
        for i in range(len(tracks)):
            if i + 1 < len(tracks):
                tracks[i]['end'] = tracks[i + 1]['start']
            else:
                tracks[i]['end'] = total_duration

        return tracks
    except Exception:
        return []


def parse_tracklist_text(text: str, total_duration: float | None = None) -> list[dict]:
    """Parse tracklist text with timestamps like '00:00 Intro', '03:45 - Track'."""
    ts_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)')
    raw_parsed = []

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        match = ts_pattern.search(line)
        if match:
            sec = parse_timestamp_to_seconds(match.group(1))
            if sec is not None:
                title = line.replace(match.group(0), '').strip(' -_[]():')
                if not title:
                    title = f"Track {len(raw_parsed)+1:02d}"
                raw_parsed.append({'start': sec, 'title': title})

    raw_parsed.sort(key=lambda x: x['start'])

    tracks = []
    for i, item in enumerate(raw_parsed, 1):
        end = raw_parsed[i]['start'] if i < len(raw_parsed) else total_duration
        tracks.append({
            'track_num': i,
            'title': item['title'],
            'start': item['start'],
            'end': end
        })

    return tracks


# ==============================================================================
# 2. Online metadata fallback (iTunes preferred → MusicBrainz)
# ==============================================================================

def fetch_album_tracklist(artist: str, album: str) -> list[dict] | None:
    """
    Query iTunes (preferred) then MusicBrainz for the album's official track list.
    Returns list of {'title': str, 'duration': float} ordered by track number, or None.
    """
    # ---- iTunes ----
    try:
        query = f"{artist} {album}".strip()
        itunes_url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
            'term': query,
            'entity': 'album',
            'limit': 1,
            'media': 'music'
        })
        req = urllib.request.Request(itunes_url, headers={'User-Agent': 'SyncDAP/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
        results = data.get('results', [])
        if results:
            collection_id = results[0].get('collectionId')
            if collection_id:
                lookup_url = (
                    f"https://itunes.apple.com/lookup?id={collection_id}&entity=song"
                )
                req2 = urllib.request.Request(lookup_url, headers={'User-Agent': 'SyncDAP/1.0'})
                with urllib.request.urlopen(req2, timeout=8) as resp2:
                    track_data = json.load(resp2)
                itunes_tracks = []
                for t in sorted(
                    track_data.get('results', []),
                    key=lambda x: x.get('trackNumber', 0)
                ):
                    if t.get('wrapperType') != 'track':
                        continue
                    t_title = t.get('trackName')
                    dur_ms = t.get('trackTimeMillis')
                    if t_title and dur_ms:
                        itunes_tracks.append({'title': t_title, 'duration': dur_ms / 1000.0})
                if itunes_tracks:
                    return itunes_tracks
    except Exception:
        pass

    # ---- MusicBrainz ----
    try:
        time.sleep(1.0)  # respect 1 req/sec rate limit
        mb_query = f'release:"{album}" AND artist:"{artist}"'
        mb_url = "https://musicbrainz.org/ws/2/release-group/?" + urllib.parse.urlencode({
            'query': mb_query,
            'fmt': 'json',
            'limit': 1
        })
        req = urllib.request.Request(mb_url, headers={'User-Agent': 'SyncDAP/1.0 (info@syncdap.local)'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            rg_data = json.load(resp)
        rg_results = rg_data.get('release-groups', [])
        if not rg_results:
            return None
        rg_id = rg_results[0].get('id')
        if not rg_id:
            return None

        # Fetch releases for the release-group and get the first one's tracks
        time.sleep(1.0)
        rel_search_url = "https://musicbrainz.org/ws/2/release/?" + urllib.parse.urlencode({
            'release-group': rg_id,
            'fmt': 'json',
            'limit': 1
        })
        req2 = urllib.request.Request(rel_search_url, headers={'User-Agent': 'SyncDAP/1.0 (info@syncdap.local)'})
        with urllib.request.urlopen(req2, timeout=8) as resp2:
            rel_list = json.load(resp2)
        releases = rel_list.get('releases', [])
        if not releases:
            return None
        rel_id = releases[0].get('id')

        time.sleep(1.0)
        rel_url = f"https://musicbrainz.org/ws/2/release/{rel_id}?" + urllib.parse.urlencode({
            'inc': 'recordings',
            'fmt': 'json'
        })
        req3 = urllib.request.Request(rel_url, headers={'User-Agent': 'SyncDAP/1.0 (info@syncdap.local)'})
        with urllib.request.urlopen(req3, timeout=8) as resp3:
            rel_data = json.load(resp3)

        mb_tracks = []
        for medium in rel_data.get('media', []):
            for tr in medium.get('tracks', []):
                t_title = tr.get('title')
                dur_ms = tr.get('length')
                if t_title and dur_ms:
                    mb_tracks.append({'title': t_title, 'duration': dur_ms / 1000.0})
        if mb_tracks:
            return mb_tracks
    except Exception:
        pass

    return None


# ==============================================================================
# 3. Silence-snap boundary refinement
# ==============================================================================

def find_silence_snap_point(file_path: str, target_sec: float, search_window: float = 3.0) -> float:
    """
    Search for silence within ±search_window around target_sec using ffmpeg silencedetect.
    Returns the centre of the nearest silence gap, or the original target if none found.
    """
    start_search = max(0.0, target_sec - search_window)
    duration = search_window * 2.0

    cmd = [
        'ffmpeg',
        '-ss', str(start_search),
        '-t', str(duration),
        '-i', file_path,
        '-af', 'silencedetect=noise=-35dB:d=0.3',
        '-f', 'null', '-'
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        output = proc.stderr
        silence_starts = [float(m.group(1)) for m in re.finditer(r'silence_start:\s*([\d.]+)', output)]
        silence_ends = [float(m.group(1)) for m in re.finditer(r'silence_end:\s*([\d.]+)', output)]

        if silence_starts and silence_ends:
            abs_start = start_search + silence_starts[0]
            abs_end = start_search + silence_ends[0]
            return (abs_start + abs_end) / 2.0
        elif silence_starts:
            return start_search + silence_starts[0]
    except Exception:
        pass

    return target_sec


# ==============================================================================
# 4. Metadata tagging
# ==============================================================================

def tag_split_track(
    track_path: str, artist: str, album: str, title: str,
    track_num: int, total_tracks: int, cover_jpg: str | None = None
):
    """Inject clean metadata into split track using mutagen."""
    ext = os.path.splitext(track_path)[1].lower()
    img_data = None
    if cover_jpg and os.path.isfile(cover_jpg):
        try:
            with open(cover_jpg, 'rb') as f:
                img_data = f.read()
        except Exception:
            pass

    try:
        if ext == '.mp3':
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, APIC
            audio = MP3(track_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))
            audio.tags.add(TALB(encoding=3, text=album))
            audio.tags.add(TRCK(encoding=3, text=f"{track_num}/{total_tracks}"))
            if img_data:
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='', data=img_data))
            audio.save(v2_version=3)

        elif ext == '.flac':
            from mutagen.flac import FLAC, Picture
            audio = FLAC(track_path)
            audio['title'] = [title]
            audio['artist'] = [artist]
            audio['album'] = [album]
            audio['tracknumber'] = [str(track_num)]
            audio['totaltracks'] = [str(total_tracks)]
            if img_data:
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3
                pic.mime = 'image/jpeg'
                pic.desc = ''
                pic.data = img_data
                audio.add_picture(pic)
            audio.save()

        elif ext == '.m4a':
            from mutagen.mp4 import MP4, MP4Cover
            audio = MP4(track_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['\xa9nam'] = [title]
            audio.tags['\xa9ART'] = [artist]
            audio.tags['\xa9alb'] = [album]
            audio.tags['trkn'] = [(track_num, total_tracks)]
            if img_data:
                audio.tags['covr'] = [MP4Cover(img_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()

    except Exception as e:
        print(f"⚠️  Tagging skipped for {os.path.basename(track_path)}: {e}")


# ==============================================================================
# 5. Main split orchestrator
# ==============================================================================

def split_album(
    audio_file: str,
    cue_file: str | None = None,
    tracklist_file: str | None = None,
    output_dir: str | None = None,
    snap_silence: bool = True,
):
    """Precision lossless split of a single-file full album into individual tracks."""
    if not os.path.isfile(audio_file):
        print(f"❌ Error: Audio file '{audio_file}' not found.")
        sys.exit(1)

    meta = get_audio_metadata(audio_file)
    artist = meta.get('artist') or "Unknown Artist"
    album = meta.get('album') or os.path.splitext(os.path.basename(audio_file))[0]
    total_dur = meta.get('duration') or 0.0

    print(f"\n🎧 Inspecting album for split: {audio_file}")
    print(f"   Artist : {artist}")
    print(f"   Album  : {album}")
    print(f"   Length : {total_dur/60:.1f} min")

    tracks: list[dict] = []

    # ── Step 1: embedded chapters ─────────────────────────────────────────────
    tracks = extract_chapters_from_file(audio_file)
    if tracks:
        print(f"   ✅ Detected {len(tracks)} embedded chapter marker(s).")

    # ── Step 2: CUE sheet (provided or auto-discovered next to audio file) ────
    if not tracks:
        cand_cue = cue_file or os.path.splitext(audio_file)[0] + '.cue'
        if os.path.isfile(cand_cue):
            tracks = parse_cue_file(cand_cue, total_dur)
            if tracks:
                print(f"   ✅ Parsed {len(tracks)} track(s) from CUE sheet: {cand_cue}")

    # ── Step 3: timestamp tracklist (.description / .txt / provided) ──────────
    if not tracks:
        cand_txt = tracklist_file
        if not cand_txt:
            for ext_try in ('.description', '.info.json', '.txt'):
                test_path = os.path.splitext(audio_file)[0] + ext_try
                if os.path.isfile(test_path):
                    cand_txt = test_path
                    break
        if cand_txt and os.path.isfile(cand_txt):
            try:
                with open(cand_txt, 'r', encoding='utf-8', errors='ignore') as tf:
                    raw_text = tf.read()
                tracks = parse_tracklist_text(raw_text, total_dur)
                if tracks:
                    print(f"   ✅ Parsed {len(tracks)} track(s) from timestamp file: {cand_txt}")
            except Exception:
                pass

    # ── Step 4: online metadata fallback (iTunes preferred → MusicBrainz) ────
    if not tracks:
        print(f"   🔎 No local track info found. Querying online metadata for \"{artist} - {album}\"...")
        fallback = fetch_album_tracklist(artist, album)
        if fallback:
            print(f"   ✅ Retrieved {len(fallback)} track(s) from online metadata.")
            cumulative = 0.0
            for i, item in enumerate(fallback, 1):
                dur = item.get('duration', 0.0)
                start = cumulative
                end = cumulative + dur if dur > 0 else None
                tracks.append({
                    'track_num': i,
                    'title': item.get('title', f'Track {i:02d}'),
                    'start': start,
                    'end': end,
                })
                if end is not None:
                    cumulative = end
        else:
            print("❌ Error: No chapters, CUE sheet, timestamp tracklist, or online metadata found.")
            print("   Try: syncdap --split <file> --tracklist <timestamps.txt>")
            print("        syncdap --split <file> --cue <file.cue>")
            sys.exit(1)

    # ── Splitting ─────────────────────────────────────────────────────────────
    target_dir = output_dir or os.path.dirname(os.path.abspath(audio_file))
    album_subdir = os.path.join(target_dir, sanitize_filename(f"{artist} - {album}"))
    os.makedirs(album_subdir, exist_ok=True)

    file_ext = os.path.splitext(audio_file)[1].lower()
    total_tracks = len(tracks)

    # Copy cover art if available next to the source
    cover_jpg = os.path.join(os.path.dirname(os.path.abspath(audio_file)), 'cover.jpg')
    dest_cover = os.path.join(album_subdir, 'cover.jpg')
    if os.path.isfile(cover_jpg) and not os.path.isfile(dest_cover):
        shutil.copy2(cover_jpg, dest_cover)

    playlist_lines: list[str] = []
    print(f"\n🚀 Splitting {total_tracks} track(s) into: {album_subdir}")

    for tr in tracks:
        idx = tr['track_num']
        raw_title = tr['title']
        clean_tit = sanitize_filename(raw_title)
        out_name = f"{idx:02d} {clean_tit} - {artist}{file_ext}"
        out_path = os.path.join(album_subdir, out_name)

        start_time = tr['start']
        end_time = tr.get('end')

        # Silence-snap refinement (skip for track 1 — it starts at 0)
        if snap_silence and idx > 1 and start_time > 0:
            start_time = find_silence_snap_point(audio_file, start_time)

        cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
               '-ss', f"{start_time:.3f}"]
        if end_time is not None and end_time > start_time:
            cmd += ['-to', f"{end_time:.3f}"]
        cmd += ['-i', audio_file, '-c', 'copy', out_path]

        subprocess.run(cmd, check=True)
        tag_split_track(out_path, artist, album, clean_tit, idx, total_tracks,
                        dest_cover if os.path.isfile(dest_cover) else None)

        print(f"   [{idx:02d}/{total_tracks:02d}] ✅ {out_name}")
        playlist_lines.append(out_name)

    # M3U8 playlist
    m3u8_path = os.path.join(album_subdir, f"{sanitize_filename(album)}.m3u8")
    with open(m3u8_path, 'w', encoding='utf-8') as pf:
        pf.write("\n".join(playlist_lines) + "\n")

    print(f"\n🎉 Split complete! {total_tracks} tracks saved to: {album_subdir}")


# ==============================================================================
# 6. CLI entry-point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Lossless album splitter. Splits a single-file album into individual tracks.\n"
            "Sources (in order of preference): embedded chapters → CUE sheet → "
            "timestamp tracklist → iTunes/MusicBrainz online metadata."
        )
    )
    parser.add_argument("audio_file", help="Path to single-file album (.flac, .mp3, .m4a, .opus).")
    parser.add_argument("--cue", help="Path to accompanying .cue sheet.")
    parser.add_argument("--tracklist", help="Path to text file with timestamps and titles.")
    parser.add_argument("-o", "--output", help="Output directory for split tracks.")
    parser.add_argument("--no-snap", action="store_true", help="Disable silence-snap boundary refinement.")
    args = parser.parse_args()

    split_album(
        args.audio_file,
        cue_file=args.cue,
        tracklist_file=args.tracklist,
        output_dir=args.output,
        snap_silence=not args.no_snap,
    )


if __name__ == "__main__":
    main()
