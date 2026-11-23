#!/usr/bin/env python3
"""Rockbox metadata audit and tag sanitization module.

Fixes <untagged> entries, normalizes split ALBUM and ALBUMARTIST tags per folder,
removes 0-byte ghost files, and enforces Rockbox-compliant ID3v2.3 tags across audio formats.
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

from share import (
    AUDIO_EXTENSIONS,
    IGNORED_DIRS,
    CLEAN_GHOST_FILES,
    clean_string,
    parse_filename_metadata,
    read_audio_metadata,
    write_audio_metadata,
)
from share.icons import ICONS


def read_track_metadata(file_path):
    """Read tags from audio file across formats using shared metadata reader."""
    ext = os.path.splitext(file_path)[1].lower()
    sz = 0
    try:
        sz = os.path.getsize(file_path)
    except OSError:
        pass

    meta = {
        'path': file_path,
        'ext': ext,
        'artist': '',
        'album': '',
        'albumartist': '',
        'title': '',
        'track_num': '',
        'valid': sz > 0,
        'size': sz,
    }

    if sz == 0:
        return meta

    try:
        raw = read_audio_metadata(file_path, fallback_to_filename=False)
        meta['artist'] = raw.get('artist', '')
        meta['album'] = raw.get('album', '')
        meta['albumartist'] = raw.get('album_artist', '')
        meta['title'] = raw.get('title', '')
        meta['track_num'] = str(raw.get('track_num', '') or '')
    except Exception:
        pass

    return meta


def write_track_metadata(file_path, new_meta):
    """Write standardized tags back to file in Rockbox-compatible format."""
    try:
        return write_audio_metadata(
            file_path,
            title=new_meta.get('title'),
            artist=new_meta.get('artist'),
            album=new_meta.get('album'),
            album_artist=new_meta.get('albumartist'),
        )
    except Exception as e:
        print(f"      {ICONS.err} Error writing metadata to {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return False


def sanitize_rockbox_metadata(root_dir, dry_run=False):
    """
    Audit and repair audio metadata across the library specifically for Rockbox DAPs:
    1. Removes 0-byte orphan files that trigger <untagged> entries.
    2. Unifies ALBUM name per directory (prevents split albums).
    3. Unifies ALBUMARTIST per directory (ensures compilations and feats group together).
    4. Fills missing TITLE and ARTIST fallback tags.
    """
    root_path = os.path.abspath(root_dir)
    print(f"\n{ICONS.tag} Rockbox Metadata Optimizer scanning: {root_path}")

    # Step 1: Scan all audio files and group by album folder
    album_folders = defaultdict(list)
    zero_byte_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]

        for f in filenames:
            if CLEAN_GHOST_FILES and (f.startswith('._') or f in ('Thumbs.db', 'desktop.ini', '.DS_Store', 'ehthumbs.db')):
                zero_byte_files.append(os.path.join(dirpath, f))
                continue

            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                full_path = os.path.join(dirpath, f)
                try:
                    if os.path.getsize(full_path) == 0:
                        zero_byte_files.append(full_path)
                        continue
                except OSError:
                    continue

                album_folders[dirpath].append(full_path)

    # Clean zero-byte ghost files
    if zero_byte_files:
        print(f"   {ICONS.warn} Found {len(zero_byte_files)} empty 0-byte audio file(s) that cause '<untagged>' in Rockbox.")
        for zf in zero_byte_files:
            rel = os.path.relpath(zf, root_path)
            print(f"      {ICONS.info} {'[DRY-RUN] Would remove' if dry_run else 'Removed 0-byte file'}: {rel}")
            if not dry_run:
                try:
                    os.remove(zf)
                except OSError as e:
                    print(f"         Error: {e}", file=sys.stderr)

    # Step 2: Process each album folder
    total_albums = len(album_folders)
    modified_tracks_count = 0
    unified_albums_count = 0

    print(f"   Auditing tags across {total_albums} album folder(s)...")

    for album_dir, track_paths in album_folders.items():
        if not track_paths:
            continue

        folder_name = os.path.basename(album_dir)
        parent_name = os.path.basename(os.path.dirname(album_dir))

        # Read metadata for all tracks in this folder
        tracks_meta = [read_track_metadata(p) for p in track_paths]
        valid_tracks = [t for t in tracks_meta if t['valid']]
        if not valid_tracks:
            continue

        # 1. Determine canonical ALBUM name for the folder
        existing_albums = [t['album'] for t in valid_tracks if t['album']]
        if existing_albums:
            # Pick the most common album name, or folder_name if tie
            counter = Counter(existing_albums)
            canonical_album = counter.most_common(1)[0][0]
        else:
            canonical_album = clean_string(folder_name)

        # 2. Determine canonical ALBUMARTIST for the folder
        existing_albumartists = [t['albumartist'] for t in valid_tracks if t['albumartist']]
        existing_artists = [t['artist'] for t in valid_tracks if t['artist']]

        if existing_albumartists:
            canonical_albumartist = Counter(existing_albumartists).most_common(1)[0][0]
        elif parent_name and parent_name not in ('.', 'Music', 'music'):
            # Parent folder is usually the primary artist
            canonical_albumartist = clean_string(parent_name)
        elif existing_artists:
            # Clean base artist without "feat."
            most_common_artist = Counter(existing_artists).most_common(1)[0][0]
            canonical_albumartist = clean_string(re.split(r'\s+(?:feat\.|ft\.|/|,)\s+', most_common_artist, flags=re.IGNORECASE)[0])
        else:
            canonical_albumartist = clean_string(parent_name or "Various Artists")

        # Check if folder has split triggers
        album_names_in_folder = set(t['album'] for t in valid_tracks)
        albumartists_in_folder = set(t['albumartist'] for t in valid_tracks)
        artists_in_folder = set(t['artist'] for t in valid_tracks)

        needs_album_unification = len(album_names_in_folder) > 1 or any(not t['album'] for t in valid_tracks)
        needs_albumartist_unification = (
            any(not t['albumartist'] for t in valid_tracks) or
            len(albumartists_in_folder) > 1 or
            (len(artists_in_folder) > 1 and canonical_albumartist not in albumartists_in_folder)
        )

        folder_modified = False

        for t in valid_tracks:
            p = t['path']
            fn_meta = parse_filename_metadata(p)

            new_title = t['title'] or fn_meta['title']
            new_artist = t['artist'] or fn_meta['artist'] or canonical_albumartist
            new_album = canonical_album
            new_albumartist = canonical_albumartist

            to_update = {}
            if t['title'] != new_title:
                to_update['title'] = new_title
            if t['artist'] != new_artist:
                to_update['artist'] = new_artist
            if t['album'] != new_album:
                to_update['album'] = new_album
            if t['albumartist'] != new_albumartist:
                to_update['albumartist'] = new_albumartist

            if to_update:
                folder_modified = True
                modified_tracks_count += 1
                if dry_run:
                    rel_p = os.path.relpath(p, root_path)
                    print(f"      [DRY-RUN] Would fix tags in {rel_p}: {to_update}")
                else:
                    write_track_metadata(p, to_update)

        if folder_modified:
            unified_albums_count += 1
            if not dry_run:
                rel_dir = os.path.relpath(album_dir, root_path)
                print(f"   {ICONS.ok} Unified album [{canonical_album}] by [{canonical_albumartist}]: {rel_dir}")

    mode_str = "[DRY-RUN] Would optimize" if dry_run else "Successfully optimized"
    print(f"\n{ICONS.ok} Rockbox Metadata summary: {mode_str} {modified_tracks_count} track(s) across {unified_albums_count} album(s).\n")
    return modified_tracks_count


def main():
    parser = argparse.ArgumentParser(description="Optimize audio tags specifically for Rockbox database compatibility.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory to scan (default: .)")
    parser.add_argument("-n", "-d", "--dry-run", action="store_true", help="Simulate without modifying files")
    args = parser.parse_args()

    root_dir = args.root_dir if args.root_dir != "." else os.environ.get("SYNCDAP_ROOT_DIR", ".")
    sanitize_rockbox_metadata(root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
