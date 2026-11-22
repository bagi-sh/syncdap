#!/usr/bin/env python3
"""Audio track deduplication and playlist relinking module.

Scans library for duplicated tracks (evaluating lossless/bitrate quality scoring),
transfers synchronized lyrics (.lrc) to the winning track, removes lower quality duplicates,
and relinks all playlists referencing purged tracks.
"""

import argparse
import os
import shutil
import sys
from collections import defaultdict

from share import (
    find_audio_files,
    get_all_playlist_files as find_playlist_files,
    get_audio_quality_score,
    normalize_str,
    parse_filename_metadata as extract_track_info,
    update_all_playlists,
)
from share.icons import ICONS


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
    print(f"\n{ICONS.find} Scanning for duplicates in: {root_path}")

    audio_files = find_audio_files(root_path)
    print(f"   Total audio files found: {len(audio_files)}")

    duplicate_groups = group_duplicates(audio_files)
    if not duplicate_groups:
        print(f"   {ICONS.ok} No audio duplicates found in library!")
        return 0, 0

    print(f"   {ICONS.warn} Found {len(duplicate_groups)} duplicate group(s) to resolve.\n")

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
        print(f"   {ICONS.music} Keep [{winner['desc']}]: {winner_rel}")

        for loser in losers:
            loser_rel = os.path.relpath(loser['path'], root_path)
            print(f"      {ICONS.info} Delete [{loser['desc']}]: {loser_rel}")

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
                        print(f"         {ICONS.info} Transferred lyrics to winner: {os.path.basename(winner_lrc)}")
                    except Exception as e:
                        print(f"         {ICONS.warn} Failed transferring .lrc: {e}")
                elif os.path.isfile(loser_lrc):
                    try:
                        os.remove(loser_lrc)
                    except OSError:
                        pass

                # Remove loser audio file
                try:
                    os.remove(loser['path'])
                except OSError as e:
                    print(f"         {ICONS.err} Error removing {loser['path']}: {e}", file=sys.stderr)

    # Playlist updates
    search_dirs = [root_path]
    if os.path.isdir(os.path.join(root_path, 'Playlists')):
        search_dirs.append(os.path.join(root_path, 'Playlists'))
    if os.path.isdir(os.path.join(os.path.dirname(root_path), 'Playlists')):
        search_dirs.append(os.path.join(os.path.dirname(root_path), 'Playlists'))
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl):
        search_dirs.append(home_pl)

    playlists = find_playlist_files(search_dirs)
    print(f"\n{ICONS.pl} Updating playlists ({len(playlists)} found)...")
    updated_pl = update_all_playlists(replacements, playlist_files=playlists, music_roots=search_dirs)

    # Perform full playlist path recovery and dead link prune
    try:
        from modules.playlist_repair import repair_playlists
    except ImportError:
        try:
            from playlist_repair import repair_playlists
        except ImportError:
            sys.path.insert(0, os.path.dirname(__file__))
            from playlist_repair import repair_playlists

    repair_playlists(root_path, dry_run=dry_run)

    mb_freed = total_bytes_freed / (1024 * 1024)
    mode_str = "[DRY-RUN] Would delete" if dry_run else "Successfully removed"
    print(f"\n{ICONS.ok} Deduplication summary: {mode_str} {total_deleted} duplicate track(s). Freed ~{mb_freed:.2f} MB. Updated {updated_pl} playlist(s).\n")

    return total_deleted, updated_pl


def main():
    parser = argparse.ArgumentParser(description="Deduplicate audio tracks keeping highest quality and update playlists.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory to scan (default: .)")
    parser.add_argument("-n", "-d", "--dry-run", action="store_true", help="Simulate without modifying files")
    args = parser.parse_args()

    run_deduplication(args.root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
