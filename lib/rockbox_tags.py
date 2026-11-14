#!/usr/bin/env python3
# ==============================================================================
# Module: lib/rockbox_tags.py
# Purpose: Deep metadata audit and sanitization specifically tailored for Rockbox.
#          - Fixes <untagged> tracks and albums.
#          - Unifies ALBUM and ALBUMARTIST tags per folder to prevent album splitting.
#          - Sets consistent Album Artist (TPE2 in ID3, aART in M4A, ALBUMARTIST in FLAC/Vorbis).
#          - Cleans 0-byte ghost files and trims rogue trailing whitespace.
#          - Enforces ID3v2.3 compatibility for Rockbox DAPs.
# ==============================================================================

import os
import sys
import re
import argparse
from collections import defaultdict, Counter

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TDRC, TCON
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

from share import (
    AUDIO_EXTENSIONS,
    IGNORED_DIRS,
    clean_string,
    parse_filename_metadata,
)


def read_track_metadata(file_path):
    """Read tags from audio file across formats."""
    ext = os.path.splitext(file_path)[1].lower()
    meta = {
        'path': file_path,
        'ext': ext,
        'artist': '',
        'album': '',
        'albumartist': '',
        'title': '',
        'track_num': '',
        'valid': False,
        'size': 0
    }

    try:
        size = os.path.getsize(file_path)
        meta['size'] = size
        if size == 0:
            return meta

        audio = mutagen.File(file_path)
        if audio is None:
            return meta

        meta['valid'] = True

        if ext == '.mp3':
            tags = getattr(audio, 'tags', None)
            if tags:
                if 'TIT2' in tags: meta['title'] = clean_string(tags['TIT2'].text[0])
                if 'TPE1' in tags: meta['artist'] = clean_string(tags['TPE1'].text[0])
                if 'TALB' in tags: meta['album'] = clean_string(tags['TALB'].text[0])
                if 'TPE2' in tags: meta['albumartist'] = clean_string(tags['TPE2'].text[0])
                if 'TRCK' in tags: meta['track_num'] = clean_string(tags['TRCK'].text[0])

        elif ext == '.m4a':
            tags = getattr(audio, 'tags', None)
            if tags:
                if '\xa9nam' in tags: meta['title'] = clean_string(tags['\xa9nam'][0])
                if '\xa9ART' in tags: meta['artist'] = clean_string(tags['\xa9ART'][0])
                if '\xa9alb' in tags: meta['album'] = clean_string(tags['\xa9alb'][0])
                if 'aART' in tags: meta['albumartist'] = clean_string(tags['aART'][0])
                if 'trkn' in tags and tags['trkn']: meta['track_num'] = str(tags['trkn'][0][0])

        elif ext in ('.flac', '.ogg', '.opus'):
            tags = getattr(audio, 'tags', None) or audio
            if tags:
                meta['title'] = clean_string(tags.get('title', [''])[0])
                meta['artist'] = clean_string(tags.get('artist', [''])[0])
                meta['album'] = clean_string(tags.get('album', [''])[0])
                meta['albumartist'] = clean_string(tags.get('albumartist', tags.get('album artist', tags.get('ALBUMARTIST', tags.get('ALBUM ARTIST', ['']))))[0])
                meta['track_num'] = clean_string(tags.get('tracknumber', [''])[0])

    except Exception:
        pass

    return meta


def write_track_metadata(file_path, new_meta):
    """Write standardized tags back to file in Rockbox-compatible format."""
    ext = os.path.splitext(file_path)[1].lower()
    modified = False

    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags

            if new_meta.get('title') and str(tags.get('TIT2', '')) != new_meta['title']:
                tags['TIT2'] = TIT2(encoding=3, text=[new_meta['title']])
                modified = True
            if new_meta.get('artist') and str(tags.get('TPE1', '')) != new_meta['artist']:
                tags['TPE1'] = TPE1(encoding=3, text=[new_meta['artist']])
                modified = True
            if new_meta.get('album') and str(tags.get('TALB', '')) != new_meta['album']:
                tags['TALB'] = TALB(encoding=3, text=[new_meta['album']])
                modified = True
            if new_meta.get('albumartist') and str(tags.get('TPE2', '')) != new_meta['albumartist']:
                tags['TPE2'] = TPE2(encoding=3, text=[new_meta['albumartist']])
                modified = True

            if modified:
                audio.save(v2_version=3)
                return True

        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags

            if new_meta.get('title') and tags.get('\xa9nam', [''])[0] != new_meta['title']:
                tags['\xa9nam'] = [new_meta['title']]
                modified = True
            if new_meta.get('artist') and tags.get('\xa9ART', [''])[0] != new_meta['artist']:
                tags['\xa9ART'] = [new_meta['artist']]
                modified = True
            if new_meta.get('album') and tags.get('\xa9alb', [''])[0] != new_meta['album']:
                tags['\xa9alb'] = [new_meta['album']]
                modified = True
            if new_meta.get('albumartist') and tags.get('aART', [''])[0] != new_meta['albumartist']:
                tags['aART'] = [new_meta['albumartist']]
                modified = True

            if modified:
                audio.save()
                return True

        elif ext in ('.flac', '.ogg', '.opus'):
            if ext == '.flac':
                audio = FLAC(file_path)
            elif ext == '.opus':
                audio = OggOpus(file_path)
            else:
                audio = OggVorbis(file_path)

            tags = audio.tags if audio.tags is not None else audio

            if new_meta.get('title') and tags.get('title', [''])[0] != new_meta['title']:
                tags['title'] = [new_meta['title']]
                modified = True
            if new_meta.get('artist') and tags.get('artist', [''])[0] != new_meta['artist']:
                tags['artist'] = [new_meta['artist']]
                modified = True
            if new_meta.get('album') and tags.get('album', [''])[0] != new_meta['album']:
                tags['album'] = [new_meta['album']]
                modified = True
            if new_meta.get('albumartist'):
                current_aa = tags.get('albumartist', tags.get('ALBUMARTIST', ['']))[0]
                if current_aa != new_meta['albumartist']:
                    tags['albumartist'] = [new_meta['albumartist']]
                    tags['ALBUMARTIST'] = [new_meta['albumartist']]
                    modified = True

            if modified:
                audio.save()
                return True

    except Exception as e:
        print(f"      ❌ Error writing metadata to {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return False

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
    print(f"\n🏷️ Rockbox Metadata Optimizer scanning: {root_path}")

    # Step 1: Scan all audio files and group by album folder
    album_folders = defaultdict(list)
    zero_byte_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]

        for f in filenames:
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
        print(f"   ⚠️ Found {len(zero_byte_files)} empty 0-byte audio file(s) that cause '<untagged>' in Rockbox.")
        for zf in zero_byte_files:
            rel = os.path.relpath(zf, root_path)
            print(f"      🗑️ {'[DRY-RUN] Would remove' if dry_run else 'Removed 0-byte file'}: {rel}")
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
                print(f"   ✅ Unified album [{canonical_album}] by [{canonical_albumartist}]: {rel_dir}")

    mode_str = "[DRY-RUN] Would optimize" if dry_run else "Successfully optimized"
    print(f"\n✨ Rockbox Metadata summary: {mode_str} {modified_tracks_count} track(s) across {unified_albums_count} album(s).\n")
    return modified_tracks_count


def main():
    parser = argparse.ArgumentParser(description="Optimize audio tags specifically for Rockbox database compatibility.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory to scan (default: .)")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate without modifying files")
    args = parser.parse_args()

    sanitize_rockbox_metadata(args.root_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
