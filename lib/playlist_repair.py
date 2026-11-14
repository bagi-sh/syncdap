#!/usr/bin/env python3
# ==============================================================================
# Module: lib/playlist_repair.py
# Purpose: Deep playlist audit & repair.
#          - Relinks broken paths when track actually exists on disk (format changes,
#            /sdcard/ prefix, Romaji/sanitized folder or filename variations).
#          - Safely removes truly orphan playlist entries whose audio is missing.
#          - Deduplicates track entries inside playlists.
#          - Normalizes relative paths to ../Music/...
# ==============================================================================

import os
import sys
import re
import argparse
from collections import defaultdict
from pathlib import Path

from share import (
    AUDIO_EXTENSIONS,
    IGNORED_DIRS,
    normalize_str as norm_str,
    get_all_playlist_files as find_all_playlists,
)


def build_library_index(music_dir):
    """
    Build memory lookup structures for audio files in music_dir:
    1. folder_map: (norm(artist_dir), norm(album_dir)) -> real_folder_path
    2. by_norm_stem: norm(stem) -> [real_paths]
    3. by_norm_fn: norm(filename) -> [real_paths]
    """
    music_dir = os.path.abspath(music_dir)
    folder_map = {}
    by_norm_stem = defaultdict(list)
    by_norm_fn = defaultdict(list)
    total_audio = 0

    for root, dirs, files in os.walk(music_dir):
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]

        rel = os.path.relpath(root, music_dir)
        parts = rel.split(os.sep)
        if len(parts) >= 2:
            key = (norm_str(parts[0]), norm_str(parts[1]))
            folder_map[key] = root

        for f in files:
            base, ext = os.path.splitext(f)
            if ext.lower() in AUDIO_EXTENSIONS:
                full_path = os.path.join(root, f)
                total_audio += 1
                by_norm_stem[norm_str(base)].append(full_path)
                by_norm_fn[norm_str(f)].append(full_path)

    return {
        'music_dir': music_dir,
        'total_audio': total_audio,
        'folder_map': folder_map,
        'by_norm_stem': by_norm_stem,
        'by_norm_fn': by_norm_fn
    }


def resolve_playlist_entry(raw_path, pl_path, index):
    """
    Resolve raw playlist path to existing file on disk using multi-layer heuristics:
    1. Direct path relative to playlist directory
    2. Clean prefix (/sdcard/Music/, ../Music/, Music/) relative to music_dir
    3. Alternative audio extensions (.flac, .m4a, .mp3, etc.)
    4. Fuzzy folder matching + track number / Romaji title
    5. Global stem matching
    Returns (resolved_abs_path, method) or (None, 'not_found').
    """
    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    music_dir = index['music_dir']

    # 1. Direct path relative to playlist dir
    direct_cand = os.path.normpath(os.path.join(pl_dir, raw_path))
    if os.path.isfile(direct_cand):
        return direct_cand, 'direct'

    # Clean known prefixes
    clean = raw_path.strip()
    for pfx in ['/sdcard/Music/', 'sdcard/Music/', '../Music/', 'Music/', './']:
        if clean.startswith(pfx):
            clean = clean[len(pfx):]
            break
    clean = clean.lstrip('/\\')

    # Direct under music_dir
    c_direct = os.path.normpath(os.path.join(music_dir, clean))
    if os.path.isfile(c_direct):
        return c_direct, 'clean_prefix'

    # 2. Alternative audio extensions
    stem, _ = os.path.splitext(c_direct)
    for ext in AUDIO_EXTENSIONS:
        cand_ext = stem + ext
        if os.path.isfile(cand_ext):
            return cand_ext, 'alt_extension'

    # 3. Fuzzy folder match + track number
    parts = clean.split('/')
    if len(parts) >= 3:
        art_part, alb_part, fn_part = parts[0], parts[1], parts[2]
        key = (norm_str(art_part), norm_str(alb_part))
        real_folder = index['folder_map'].get(key)
        if real_folder and os.path.isdir(real_folder):
            cand_fn = os.path.join(real_folder, fn_part)
            if os.path.isfile(cand_fn):
                return cand_fn, 'folder_norm'

            f_stem, _ = os.path.splitext(fn_part)
            for ext in AUDIO_EXTENSIONS:
                cand_fe = os.path.join(real_folder, f_stem + ext)
                if os.path.isfile(cand_fe):
                    return cand_fe, 'folder_norm_altext'

            # Match by track number in real folder (handles Japanese -> Romaji renaming)
            match_tnum = re.match(r'^(\d+)', fn_part)
            if match_tnum:
                tnum = str(int(match_tnum.group(1))).zfill(2)
                t_candidates = []
                for af in os.listdir(real_folder):
                    m_af = re.match(r'^(\d+)', af)
                    if m_af and str(int(m_af.group(1))).zfill(2) == tnum:
                        if os.path.splitext(af)[1].lower() in AUDIO_EXTENSIONS:
                            t_candidates.append(os.path.join(real_folder, af))
                if len(t_candidates) == 1:
                    return t_candidates[0], 'track_number_romaji'

    # 4. Global match by normalized stem
    fn = os.path.basename(clean)
    base, _ = os.path.splitext(fn)
    n_base = norm_str(base)
    if n_base in index['by_norm_stem'] and len(index['by_norm_stem'][n_base]) == 1:
        return index['by_norm_stem'][n_base][0], 'global_stem_match'

    # 5. Global match by normalized filename
    n_fn = norm_str(fn)
    if n_fn in index['by_norm_fn'] and len(index['by_norm_fn'][n_fn]) == 1:
        return index['by_norm_fn'][n_fn][0], 'global_fn_match'

    return None, 'not_found'


def repair_playlists(root_dir, dry_run=False):
    """
    Scan and repair all playlists:
    - Relinks paths where the song exists on disk.
    - Prunes truly non-existent tracks.
    - Deduplicates identical entries within each playlist.
    """
    root_path = os.path.abspath(root_dir)
    music_dir = root_path
    if os.path.isdir(os.path.join(root_path, 'Music')):
        music_dir = os.path.join(root_path, 'Music')

    print(f"\n📋 Playlist Auditor scanning music at: {music_dir}")
    index = build_library_index(music_dir)
    print(f"   Indexed {index['total_audio']:,} audio files in library.\n")

    # Candidate playlist directories
    search_dirs = [
        root_path,
        os.path.join(root_path, 'Playlists'),
        os.path.join(os.path.dirname(root_path), 'Playlists')
    ]
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl):
        search_dirs.append(home_pl)

    playlists = find_all_playlists(search_dirs)
    if not playlists:
        print("   ℹ️ No playlist files (.m3u/.m3u8) found to audit.")
        return 0, 0, 0

    print(f"   Auditing {len(playlists)} playlist file(s)...")

    total_relinked = 0
    total_pruned = 0
    playlists_modified = 0

    for pl_path in playlists:
        pl_dir = os.path.dirname(pl_path)
        pl_name = os.path.basename(pl_path)

        try:
            with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_lines = f.readlines()
        except Exception as e:
            print(f"   ⚠️ Could not read {pl_name}: {e}")
            continue

        new_lines = []
        pending_extinf = None
        seen_tracks_in_pl = set()
        pl_relinked = 0
        pl_pruned = 0
        pl_changed = False

        for line in raw_lines:
            s = line.strip()
            if not s:
                continue

            if s.startswith('#EXTM3U'):
                continue
            elif s.startswith('#EXTINF'):
                pending_extinf = s
                continue
            elif s.startswith('#'):
                # Other metadata comment
                new_lines.append(s)
                continue

            # Audio entry line
            resolved, method = resolve_playlist_entry(s, pl_path, index)

            if resolved:
                # Track exists on disk!
                rel_path = os.path.relpath(resolved, pl_dir)
                norm_key = os.path.abspath(resolved).lower()

                # Deduplicate inside playlist
                if norm_key in seen_tracks_in_pl:
                    # Duplicate entry in playlist: skip
                    pl_changed = True
                    pending_extinf = None
                    continue

                seen_tracks_in_pl.add(norm_key)

                if method != 'direct' or rel_path != s:
                    pl_relinked += 1
                    total_relinked += 1
                    pl_changed = True

                if pending_extinf:
                    new_lines.append(pending_extinf)
                    pending_extinf = None
                new_lines.append(rel_path)

            else:
                # Track truly missing from library
                pl_pruned += 1
                total_pruned += 1
                pl_changed = True
                pending_extinf = None  # drop orphaned EXTINF

        if pl_changed:
            playlists_modified += 1
            new_lines.insert(0, '#EXTM3U')
            status_desc = []
            if pl_relinked:
                status_desc.append(f"{pl_relinked} relinked")
            if pl_pruned:
                status_desc.append(f"{pl_pruned} missing pruned")

            detail_str = ', '.join(status_desc) or "deduplicated"
            print(f"   📝 {'[DRY-RUN] Would repair' if dry_run else 'Repaired'} {pl_name}: ({detail_str}, {len(seen_tracks_in_pl)} valid tracks)")

            if not dry_run:
                try:
                    with open(pl_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines) + '\n')
                except Exception as e:
                    print(f"      ❌ Error writing {pl_name}: {e}")

    mode_str = "[DRY-RUN] Would update" if dry_run else "Successfully updated"
    print(f"\n✨ Playlist audit summary: {mode_str} {playlists_modified} playlist(s). {total_relinked} track(s) recovered/relinked, {total_pruned} missing track(s) pruned.\n")

    return playlists_modified, total_relinked, total_pruned


def main():
    parser = argparse.ArgumentParser(description="Audit and repair playlists: relink existing tracks and prune missing.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory (default: .)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate without modifying playlist files")
    args = parser.parse_args()

    repair_playlists(args.root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
