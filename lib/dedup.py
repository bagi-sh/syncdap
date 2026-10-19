#!/usr/bin/env python3
# ==============================================================================
# Module: lib/dedup.py
# Purpose: Library-wide audio deduplication (FLAC > WAV > M4A > OPUS > OGG > MP3),
#          bitrate/lossless aware scoring, .lrc transfer, and automatic M3U/M3U8
#          playlist relinking and entry deduplication.
# ==============================================================================

import os
import sys
import re
import shutil
import argparse
from collections import defaultdict
from pathlib import Path

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE

AUDIO_EXTENSIONS = ('.flac', '.wav', '.m4a', '.opus', '.ogg', '.mp3')
IGNORED_DIRS = {
    'lost.dir', '.trash-1000', '.trash', 'system volume information',
    '.android_secure', '.rockbox', 'backup', '__pycache__'
}


def normalize_str(s):
    if not s:
        return ""
    # Strip whitespace, lower case, remove punctuation for loose matching
    s = s.lower().strip()
    s = re.sub(r'[\s_\-]+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()


def get_audio_quality_score(file_path):
    """
    Compute a numerical quality score for audio file.
    Higher is better.
    Lossless (FLAC, ALAC, WAV) > Lossy (AAC/M4A, OPUS, OGG, MP3).
    Within lossy: Bitrate + format baseline.
    Corrupted or 0-byte files return -1.
    """
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return -1, "0-byte file"
    except OSError:
        return -1, "unreadable"

    ext = os.path.splitext(file_path)[1].lower()

    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return 0, f"unknown {ext}"

        # 1. FLAC (Lossless)
        if ext == '.flac' or isinstance(audio, FLAC):
            sample_rate = getattr(audio.info, 'sample_rate', 44100) or 44100
            bits = getattr(audio.info, 'bits_per_sample', 16) or 16
            # Base 1,000,000 + bits * 10,000 + sample_rate
            score = 1000000 + (bits * 10000) + sample_rate
            return score, f"FLAC {bits}-bit {sample_rate}Hz"

        # 2. WAV (Lossless)
        if ext == '.wav' or isinstance(audio, WAVE):
            sample_rate = getattr(audio.info, 'sample_rate', 44100) or 44100
            bits = getattr(audio.info, 'bits_per_sample', 16) or 16
            score = 900000 + (bits * 10000) + sample_rate
            return score, f"WAV {bits}-bit {sample_rate}Hz"

        # 3. M4A (ALAC Lossless or AAC Lossy)
        if ext == '.m4a' or isinstance(audio, MP4):
            # Check if ALAC
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            channels = getattr(audio.info, 'channels', 2) or 2
            bitrate_kbps = bitrate // 1000 if bitrate else 0

            # Mutagen MP4 info codec check
            codec = getattr(audio.info, 'codec', '')
            if 'alac' in str(codec).lower():
                return 950000, "ALAC Lossless"

            # AAC Lossy: base 500,000 + bitrate_kbps
            if bitrate_kbps == 0 and getattr(audio.info, 'length', 0) > 0:
                bitrate_kbps = int((size * 8) / (audio.info.length * 1000))

            score = 500000 + bitrate_kbps
            return score, f"M4A/AAC ~{bitrate_kbps}kbps"

        # 4. OPUS
        if ext == '.opus' or isinstance(audio, OggOpus):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 160
            score = 450000 + bitrate_kbps
            return score, f"OPUS ~{bitrate_kbps}kbps"

        # 5. OGG Vorbis
        if ext == '.ogg' or isinstance(audio, OggVorbis):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 192
            score = 400000 + bitrate_kbps
            return score, f"OGG ~{bitrate_kbps}kbps"

        # 6. MP3
        if ext == '.mp3' or isinstance(audio, MP3):
            bitrate = getattr(audio.info, 'bitrate', 0) or 0
            bitrate_kbps = bitrate // 1000 if bitrate else 320
            score = 300000 + bitrate_kbps
            return score, f"MP3 ~{bitrate_kbps}kbps"

    except Exception as e:
        return 10, f"error reading tags: {e}"

    return 50, f"fallback {ext}"


def find_audio_files(root_dir):
    """Scan root_dir recursively for audio files excluding ignored system directories."""
    audio_files = []
    root_path = os.path.abspath(root_dir)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter ignored directories in-place
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]

        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                audio_files.append(os.path.join(dirpath, f))

    return audio_files


def extract_track_info(file_path):
    """Extract basic identifiers (track number, title, artist, album, stem) from audio file."""
    base_name = os.path.basename(file_path)
    stem, ext = os.path.splitext(base_name)
    parent_dir = os.path.dirname(os.path.abspath(file_path))
    album_dir = os.path.basename(parent_dir)
    artist_dir = os.path.basename(os.path.dirname(parent_dir))

    track_no = ""
    title = ""
    artist = ""
    album = ""

    # Parse filename heuristic: "01 Title - Artist" or "01 - Title"
    match = re.match(r'^(\d+)\s*[-._\s]\s*(.*)$', stem)
    if match:
        track_no = str(int(match.group(1)))
        rest = match.group(2).strip()
        if ' - ' in rest:
            parts = rest.split(' - ')
            title = ' - '.join(parts[:-1]).strip()
            artist = parts[-1].strip()
        else:
            title = rest
    elif ' - ' in stem:
        parts = stem.split(' - ')
        title = ' - '.join(parts[:-1]).strip()
        artist = parts[-1].strip()
    else:
        title = stem

    return {
        'path': file_path,
        'stem': stem,
        'ext': ext.lower(),
        'parent_dir': parent_dir,
        'album_dir': album_dir,
        'artist_dir': artist_dir,
        'track_no': track_no,
        'title': title,
        'artist': artist
    }


def group_duplicates(audio_files):
    """
    Group audio files that represent the same track.
    1. Primary: Same album folder and same stem (different extensions).
    2. Secondary: Same album folder with same track number and normalized title.
    """
    stem_groups = defaultdict(list)
    track_title_groups = defaultdict(list)

    for p in audio_files:
        info = extract_track_info(p)
        parent = info['parent_dir']
        norm_stem = normalize_str(info['stem'])

        # Group by folder + stem
        stem_groups[(parent, norm_stem)].append(info)

        # Group by folder + track_no + norm_title (if track_no exists)
        if info['track_no']:
            norm_title = normalize_str(info['title'])
            track_title_groups[(parent, info['track_no'], norm_title)].append(info)

    all_groups = []
    seen_files = set()

    # 1. Collect direct stem matches
    for (parent, norm_stem), group in stem_groups.items():
        if len(group) > 1:
            group_paths = tuple(sorted(item['path'] for item in group))
            if group_paths not in seen_files:
                seen_files.add(group_paths)
                all_groups.append(group)

    # 2. Collect track_no + title matches not already grouped
    for (parent, track_no, norm_title), group in track_title_groups.items():
        if len(group) > 1:
            group_paths = tuple(sorted(item['path'] for item in group))
            # Check if any file was already part of an exact stem group
            already_covered = any(any(item['path'] in g_paths for item in group) for g_paths in seen_files)
            if not already_covered:
                seen_files.add(group_paths)
                all_groups.append(group)

    return all_groups


def find_playlist_files(search_roots):
    """Find all .m3u and .m3u8 playlists across candidate directories."""
    playlist_files = set()

    for r in search_roots:
        if not r or not os.path.exists(r):
            continue
        r = os.path.abspath(r)

        # Check candidate locations
        dirs_to_check = [
            r,
            os.path.join(r, 'Playlists'),
            os.path.join(r, 'playlists'),
            os.path.join(os.path.dirname(r), 'Playlists'),
            os.path.join(os.path.dirname(r), 'playlists'),
        ]

        for d in dirs_to_check:
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.lower().endswith(('.m3u8', '.m3u')):
                        playlist_files.add(os.path.abspath(os.path.join(d, f)))

    return sorted(list(playlist_files))


def resolve_playlist_line(line, pl_dir, music_roots):
    """Resolve a raw playlist line to an absolute file path on disk."""
    raw = line.strip()
    if not raw or raw.startswith('#'):
        return None

    clean = raw.lstrip('/\\')
    if clean.startswith('sdcard/'):
        clean = clean[7:]
    elif clean.startswith('Music/'):
        clean = clean[6:]

    # 1. Direct relative to playlist directory
    p = os.path.normpath(os.path.join(pl_dir, raw))
    if os.path.isfile(p):
        return os.path.abspath(p)

    # 2. Relative to parent of playlist directory (e.g. DAP root)
    p_parent = os.path.normpath(os.path.join(os.path.dirname(pl_dir), clean))
    if os.path.isfile(p_parent):
        return os.path.abspath(p_parent)

    # 3. Check within music roots
    for root in music_roots:
        cand1 = os.path.normpath(os.path.join(root, clean))
        if os.path.isfile(cand1):
            return os.path.abspath(cand1)
        cand2 = os.path.normpath(os.path.join(root, 'Music', clean))
        if os.path.isfile(cand2):
            return os.path.abspath(cand2)

    return os.path.abspath(p)


def update_playlists(replacements, playlist_files, music_roots):
    """
    Update playlists substituting replaced/deleted audio paths with the winner path.
    Also deduplicates duplicate entries within the playlist.
    """
    if not replacements or not playlist_files:
        return 0

    norm_replacements = {os.path.abspath(k): os.path.abspath(v) for k, v in replacements.items()}
    updated_pl_count = 0

    for pl_path in playlist_files:
        pl_dir = os.path.dirname(pl_path)
        try:
            with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            continue

        new_lines = []
        has_changes = False
        seen_tracks_in_pl = set()

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('#'):
                new_lines.append(stripped)
                continue

            resolved = resolve_playlist_line(stripped, pl_dir, music_roots)
            target_track = resolved

            if resolved in norm_replacements:
                target_track = norm_replacements[resolved]
                has_changes = True

            # If target_track was already added, skip duplicate entry in playlist
            target_track_abs = os.path.abspath(target_track) if target_track else None
            if target_track_abs in seen_tracks_in_pl:
                # Remove preceding #EXTINF if present
                if new_lines and new_lines[-1].startswith('#EXTINF'):
                    new_lines.pop()
                has_changes = True
                continue

            seen_tracks_in_pl.add(target_track_abs)

            # Compute relative path from playlist dir to target_track
            if os.path.isfile(target_track):
                rel_path = os.path.relpath(target_track, pl_dir)
                if rel_path != stripped:
                    new_lines.append(rel_path)
                    has_changes = True
                else:
                    new_lines.append(stripped)
            else:
                new_lines.append(stripped)

        if has_changes:
            try:
                # Ensure #EXTM3U header
                if not new_lines or not new_lines[0].startswith('#EXTM3U'):
                    new_lines.insert(0, '#EXTM3U')

                with open(pl_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines) + '\n')
                updated_pl_count += 1
                print(f"   [PLAYLIST UPDATED] {os.path.basename(pl_path)}")
            except Exception as e:
                print(f"   [PLAYLIST ERROR] Could not save {pl_path}: {e}", file=sys.stderr)

    return updated_pl_count


def run_deduplication(root_dir, dry_run=False):
    """
    Main entry point for deduplicating audio files.
    - Scans root_dir for duplicate tracks.
    - Evaluates quality score (Lossless > Lossy, Bitrate).
    - Preserves/transfers .lrc lyrics file to winning track.
    - Deletes lower-quality duplicates.
    - Updates all relevant playlists.
    """
    root_path = os.path.abspath(root_dir)
    print(f"\n🔍 Scanning for duplicates in: {root_path}")

    audio_files = find_audio_files(root_path)
    print(f"   Total audio files found: {len(audio_files)}")

    duplicate_groups = group_duplicates(audio_files)
    if not duplicate_groups:
        print("   ✅ No audio duplicates found in library!")
        return 0, 0

    print(f"   ⚠️ Found {len(duplicate_groups)} duplicate group(s) to resolve.\n")

    replacements = {}
    total_deleted = 0
    total_bytes_freed = 0

    for group in duplicate_groups:
        # Score each candidate in group
        scored = []
        for item in group:
            score, desc = get_audio_quality_score(item['path'])
            try:
                sz = os.path.getsize(item['path'])
            except OSError:
                sz = 0
            scored.append({
                'path': item['path'],
                'ext': item['ext'],
                'score': score,
                'desc': desc,
                'size': sz
            })

        # Sort: highest score first, tie-break by size
        scored.sort(key=lambda x: (x['score'], x['size']), reverse=True)

        winner = scored[0]
        losers = scored[1:]

        winner_rel = os.path.relpath(winner['path'], root_path)
        print(f"   🎵 Keep [{winner['desc']}]: {winner_rel}")

        for loser in losers:
            loser_rel = os.path.relpath(loser['path'], root_path)
            print(f"      🗑️ Delete [{loser['desc']}]: {loser_rel}")

            total_deleted += 1
            total_bytes_freed += loser['size']
            replacements[loser['path']] = winner['path']

            if not dry_run:
                # Transfer .lrc if loser has one and winner doesn't
                loser_lrc = os.path.splitext(loser['path'])[0] + '.lrc'
                winner_lrc = os.path.splitext(winner['path'])[0] + '.lrc'

                if os.path.isfile(loser_lrc) and not os.path.isfile(winner_lrc):
                    try:
                        shutil.move(loser_lrc, winner_lrc)
                        print(f"         📝 Transferred lyrics to winner: {os.path.basename(winner_lrc)}")
                    except Exception as e:
                        print(f"         ⚠️ Failed transferring .lrc: {e}")
                elif os.path.isfile(loser_lrc):
                    try:
                        os.remove(loser_lrc)
                    except OSError:
                        pass

                # Remove loser audio file
                try:
                    os.remove(loser['path'])
                except OSError as e:
                    print(f"         ❌ Error removing {loser['path']}: {e}", file=sys.stderr)

    # Playlist updates
    search_dirs = [root_path]
    if os.path.isdir(os.path.join(root_path, 'Playlists')):
        search_dirs.append(os.path.join(root_path, 'Playlists'))
    if os.path.isdir(os.path.join(os.path.dirname(root_path), 'Playlists')):
        search_dirs.append(os.path.join(os.path.dirname(root_path), 'Playlists'))
    # Also check /home/bagi/Music, /home/bagi/Playlists
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl):
        search_dirs.append(home_pl)

    playlists = find_playlist_files(search_dirs)
    print(f"\n📋 Updating playlists ({len(playlists)} found)...")
    updated_pl = update_playlists(replacements, playlists, search_dirs)

    # Perform full playlist path recovery and dead link prune
    try:
        from playlist_repair import repair_playlists
    except ImportError:
        sys.path.insert(0, os.path.dirname(__file__))
        from playlist_repair import repair_playlists

    repair_playlists(root_path, dry_run=dry_run)

    mb_freed = total_bytes_freed / (1024 * 1024)
    mode_str = "[DRY-RUN] Would delete" if dry_run else "Successfully removed"
    print(f"\n✨ Deduplication summary: {mode_str} {total_deleted} duplicate track(s). Freed ~{mb_freed:.2f} MB. Updated {updated_pl} playlist(s).\n")

    return total_deleted, updated_pl


def main():
    parser = argparse.ArgumentParser(description="Deduplicate audio tracks keeping highest quality and update playlists.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory to scan (default: .)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate without modifying files")
    args = parser.parse_args()

    run_deduplication(args.root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
