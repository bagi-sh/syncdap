#!/usr/bin/env python3
"""Playlist repair and path relinking module.

Audits playlist files (.m3u/.m3u8), relinks moved or reformatted tracks to their canonical
audio files, prunes dead links, deduplicates entries, and normalizes relative directory paths.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from share import (
    AUDIO_EXTENSIONS,
    IGNORED_DIRS,
    normalize_str as norm_str,
    get_all_playlist_files as find_all_playlists,
)
from share.icons import ICONS


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
    3. Folder mapping (artist/album) + stem or filename match
    4. Exact filename match anywhere in music_dir
    5. Exact stem match anywhere in music_dir (format change FLAC/MP3/M4A)
    6. Normalized stem fuzzy match
    """
    music_dir = index['music_dir']
    pl_dir = os.path.dirname(pl_path)

    # Clean Windows backslashes and quotes
    cleaned = raw_path.strip().strip('"\'').replace('\\', '/')

    # 1. Direct path check
    direct = os.path.normpath(os.path.join(pl_dir, cleaned))
    if os.path.isfile(direct):
        return direct, 'direct'

    # Direct from music_dir
    direct_music = os.path.normpath(os.path.join(music_dir, cleaned))
    if os.path.isfile(direct_music):
        return direct_music, 'direct_music'

    # 2. Strip common prefixes
    rel_clean = cleaned
    for prefix in ['/sdcard/Music/', 'sdcard/Music/', '/storage/emulated/0/Music/', '../Music/', 'Music/', './']:
        if rel_clean.startswith(prefix):
            rel_clean = rel_clean[len(prefix):]
            break

    stripped_path = os.path.normpath(os.path.join(music_dir, rel_clean))
    if os.path.isfile(stripped_path):
        return stripped_path, 'prefix_stripped'

    parts = [p for p in rel_clean.split('/') if p and p != '.']
    fn = parts[-1] if parts else os.path.basename(cleaned)
    stem, ext = os.path.splitext(fn)

    # 3. Check within same folder if artist/album folder matched
    if len(parts) >= 3:
        artist_folder = parts[-3]
        album_folder = parts[-2]
        key = (norm_str(artist_folder), norm_str(album_folder))
        real_folder = index['folder_map'].get(key)
        if real_folder:
            # Check exact filename
            target = os.path.join(real_folder, fn)
            if os.path.isfile(target):
                return target, 'folder_match'
            # Check any audio with same stem (format change)
            for cand in index['by_norm_stem'].get(norm_str(stem), []):
                if os.path.commonpath([cand, real_folder]) == real_folder:
                    return cand, 'folder_stem_match'

    # 4. Global match by exact filename
    fn_matches = index['by_norm_fn'].get(norm_str(fn), [])
    if len(fn_matches) == 1:
        return fn_matches[0], 'unique_filename'

    # 5. Global match by stem (e.g. format change .flac -> .mp3 or vice versa)
    stem_matches = index['by_norm_stem'].get(norm_str(stem), [])
    if len(stem_matches) == 1:
        return stem_matches[0], 'unique_stem'

    # If multiple stem matches, prefer one with matching parent album folder
    if len(stem_matches) > 1 and len(parts) >= 2:
        parent_hint = norm_str(parts[-2])
        filtered = [p for p in stem_matches if parent_hint in norm_str(os.path.basename(os.path.dirname(p)))]
        if len(filtered) == 1:
            return filtered[0], 'stem_album_hint'

    # 6. Romaji / Stripped special chars fuzzy stem match
    fuzzy_norm = re.sub(r'[^a-z0-9]', '', norm_str(stem))
    if fuzzy_norm:
        candidates = []
        for indexed_stem, paths in index['by_norm_stem'].items():
            if re.sub(r'[^a-z0-9]', '', indexed_stem) == fuzzy_norm:
                candidates.extend(paths)
        if len(candidates) == 1:
            return candidates[0], 'fuzzy_stem'

    return None, 'missing'


def repair_playlists(root_dir, dry_run=False):
    """
    Main entry point for auditing and repairing playlists.
    - Resolves broken paths for existing library tracks.
    - Prunes missing tracks.
    - Normalizes relative paths.
    - Deduplicates identical track entries inside the same playlist.
    """
    root_path = os.path.abspath(root_dir)
    music_dir = root_path
    if os.path.isdir(os.path.join(root_path, 'Music')):
        music_dir = os.path.join(root_path, 'Music')

    print(f"\n{ICONS.pl} Playlist Auditor scanning music at: {music_dir}")
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
        print(f"   {ICONS.info} No playlist files (.m3u/.m3u8) found to audit.")
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
            print(f"   {ICONS.warn} Could not read {pl_name}: {e}")
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
            print(f"   {ICONS.info} {'[DRY-RUN] Would repair' if dry_run else 'Repaired'} {pl_name}: ({detail_str}, {len(seen_tracks_in_pl)} valid tracks)")

            if not dry_run:
                try:
                    with open(pl_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines) + '\n')
                except Exception as e:
                    print(f"      {ICONS.err} Error writing {pl_name}: {e}")

    mode_str = "[DRY-RUN] Would update" if dry_run else "Successfully updated"
    print(f"\n{ICONS.ok} Playlist audit summary: {mode_str} {playlists_modified} playlist(s). {total_relinked} track(s) recovered/relinked, {total_pruned} missing track(s) pruned.\n")

    return playlists_modified, total_relinked, total_pruned


def main():
    parser = argparse.ArgumentParser(description="Audit and repair playlists: relink existing tracks and prune missing.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory (default: .)")
    parser.add_argument("-n", "-d", "--dry-run", action="store_true", help="Simulate without modifying playlist files")
    args = parser.parse_args()

    repair_playlists(args.root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
