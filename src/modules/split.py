#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/split.py
# Purpose: Precision lossless album splitter using chapters, CUE sheets, and silence-snapping
# ==============================================================================

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from share import (
    AUDIO_EXTENSIONS,
    clean_string,
    get_audio_metadata,
    parse_timestamp_to_seconds,
    sanitize_filename,
)


def extract_chapters_from_file(file_path: str) -> list[dict]:
    """Extract embedded chapter markers via ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
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
            tracks.append({
                'track_num': i,
                'title': title,
                'start': start,
                'end': end
            })
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
            # Match TRACK 01 AUDIO
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

                # Match INDEX 01 04:12:35 (mm:ss:ff -> 75 frames/sec)
                m_index = re.match(r'^INDEX\s+01\s+(\d+):(\d+):(\d+)', line, re.IGNORECASE)
                if m_index:
                    m, s, f = int(m_index.group(1)), int(m_index.group(2)), int(m_index.group(3))
                    start_sec = m * 60.0 + s + (f / 75.0)
                    current_track['start'] = start_sec

        if current_track:
            tracks.append(current_track)

        # Calculate end timestamps
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
    tracks = []
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    # Pattern: [00:00] or 00:00 or 01:23:45 followed or preceded by title
    ts_pattern = re.compile(r'(\d{1,2}:\d{2}(?::\d{2})?)')

    raw_parsed = []
    for line in lines:
        match = ts_pattern.search(line)
        if match:
            ts_str = match.group(1)
            sec = parse_timestamp_to_seconds(ts_str)
            if sec is not None:
                # Remove timestamp from line to get title
                title = line.replace(match.group(0), '').strip(' -_[]():')
                if not title:
                    title = f"Track {len(raw_parsed)+1:02d}"
                raw_parsed.append({'start': sec, 'title': title})

    raw_parsed.sort(key=lambda x: x['start'])

    for i, item in enumerate(raw_parsed, 1):
        end = raw_parsed[i]['start'] if i < len(raw_parsed) else total_duration
        tracks.append({
            'track_num': i,
            'title': item['title'],
            'start': item['start'],
            'end': end
        })

    return tracks


def find_silence_snap_point(file_path: str, target_sec: float, search_window: float = 3.0) -> float:
    """
    Search for silence within ±search_window around target_sec using ffmpeg silencedetect.
    Snaps target point to the silence gap for clean, click-free track transitions.
    """
    start_search = max(0.0, target_sec - search_window)
    duration = search_window * 2.0

    cmd = [
        'ffmpeg',
        '-ss', str(start_search),
        '-t', str(duration),
        '-i', file_path,
        '-af', 'silencedetect=noise=-35dB:d=0.3',
        '-f', 'null',
        '-'
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        output = proc.stderr

        # Look for silence_start: X or silence_end: Y
        silence_starts = [float(m.group(1)) for m in re.finditer(r'silence_start:\s*([\d.]+)', output)]
        silence_ends = [float(m.group(1)) for m in re.finditer(r'silence_end:\s*([\d.]+)', output)]

        if silence_starts and silence_ends:
            # Map back to absolute file position
            abs_start = start_search + silence_starts[0]
            abs_end = start_search + silence_ends[0]
            # Center cut point in middle of silence
            return (abs_start + abs_end) / 2.0
        elif silence_starts:
            return start_search + silence_starts[0]
    except Exception:
        pass

    return target_sec


def tag_split_track(track_path: str, artist: str, album: str, title: str,
                    track_num: int, total_tracks: int, cover_jpg: str | None = None):
    """Inject clean metadata into split track."""
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
    except Exception:
        pass


def split_album(audio_file: str, cue_file: str | None = None,
                tracklist_file: str | None = None, output_dir: str | None = None,
                snap_silence: bool = True):
    """Precision split of single-file full album into individual tracks."""
    if not os.path.isfile(audio_file):
        print(f"❌ Error: Audio file '{audio_file}' not found.")
        sys.exit(1)

    meta = get_audio_metadata(audio_file)
    artist = meta.get('artist') or "Unknown Artist"
    album = meta.get('album') or os.path.splitext(os.path.basename(audio_file))[0]
    total_dur = meta.get('duration') or 0.0

    print(f"\n🎧 Inspecting album for split: {audio_file}")
    print(f"   Artist: {artist} | Album: {album} | Length: {total_dur/60:.1f} min")

    tracks = []

    # 1. Check embedded chapters
    tracks = extract_chapters_from_file(audio_file)
    if tracks:
        print(f"   ✅ Detected {len(tracks)} embedded chapter marker(s).")

    # 2. Check external/provided CUE file
    if not tracks:
        cand_cue = cue_file or os.path.splitext(audio_file)[0] + '.cue'
        if os.path.isfile(cand_cue):
            tracks = parse_cue_file(cand_cue, total_dur)
            if tracks:
                print(f"   ✅ Parsed {len(tracks)} track(s) from CUE sheet: {cand_cue}")

    # 3. Check tracklist text file (or yt-dlp .description / .info.json)
    if not tracks:
        cand_txt = tracklist_file
        if not cand_txt:
            for ext in ('.description', '.info.json', '.txt'):
                test_path = os.path.splitext(audio_file)[0] + ext
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

    if not tracks:
        print("❌ Error: No chapters, CUE sheet, or timestamp tracklist found.")
        print("Please provide a tracklist with timestamps using '--tracklist <file>' or '--cue <file.cue>'.")
        sys.exit(1)

    target_dir = output_dir or os.path.dirname(os.path.abspath(audio_file))
    album_subdir = os.path.join(target_dir, sanitize_filename(f"{artist} - {album}"))
    os.makedirs(album_subdir, exist_ok=True)

    ext = os.path.splitext(audio_file)[1].lower()
    total_tracks = len(tracks)

    # Copy cover art if available
    cover_jpg = os.path.join(os.path.dirname(os.path.abspath(audio_file)), 'cover.jpg')
    dest_cover = os.path.join(album_subdir, 'cover.jpg')
    if os.path.isfile(cover_jpg) and not os.path.isfile(dest_cover):
        shutil.copy2(cover_jpg, dest_cover)

    playlist_lines = []
    print(f"\n🚀 Splitting {total_tracks} track(s) into: {album_subdir}...")

    for tr in tracks:
        idx = tr['track_num']
        raw_title = tr['title']
        clean_tit = sanitize_filename(raw_title)
        out_name = f"{idx:02d} {clean_tit} - {artist}{ext}"
        out_path = os.path.join(album_subdir, out_name)

        start_time = tr['start']
        end_time = tr['end']

        # Precision refinement: snap to silence boundary if enabled
        if snap_silence and idx > 1 and start_time > 0:
            start_time = find_silence_snap_point(audio_file, start_time)

        cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error']
        cmd += ['-ss', f"{start_time:.3f}"]
        if end_time is not None and end_time > start_time:
            cmd += ['-to', f"{end_time:.3f}"]
        cmd += ['-i', audio_file, '-c', 'copy', out_path]

        subprocess.run(cmd, check=True)
        tag_split_track(out_path, artist, album, clean_tit, idx, total_tracks, dest_cover)

        print(f"   [{idx:02d}/{total_tracks:02d}] ✅ {out_name}")
        playlist_lines.append(out_name)

    # Generate M3U8 playlist
    m3u8_path = os.path.join(album_subdir, f"{sanitize_filename(album)}.m3u8")
    with open(m3u8_path, 'w', encoding='utf-8') as pf:
        pf.write("\n".join(playlist_lines) + "\n")

    print(f"\n🎉 Split completed! {total_tracks} tracks and playlist saved to: {album_subdir}")


def main():
    parser = argparse.ArgumentParser(description="Lossless album splitter for single-file full albums.")
    parser.add_argument("audio_file", help="Path to single-file album audio (.flac, .mp3, .m4a, .opus).")
    parser.add_argument("--cue", help="Optional path to accompanying .cue sheet.")
    parser.add_argument("--tracklist", help="Optional path to text file containing timestamps and titles.")
    parser.add_argument("-o", "--output", help="Output directory for split tracks.")
    parser.add_argument("--no-snap", action="store_true", help="Disable silence-snapping refinement.")
    args = parser.parse_args()

    split_album(
        args.audio_file,
        cue_file=args.cue,
        tracklist_file=args.tracklist,
        output_dir=args.output,
        snap_silence=not args.no_snap
    )


if __name__ == "__main__":
    main()
