#!/usr/bin/env python3
# ==============================================================================
# Module: src/stats.py
# Purpose: Comprehensive music library analytics & status dashboard for Rockbox / DAPs.
#          Tracks, albums, artists, format breakdown, bitrate, lyrics (synced vs unsynced),
#          cover art status (embedded vs standalone cover.jpg), disk space, and tag health.
# ==============================================================================

import os
import sys
import re
import argparse
from collections import defaultdict, Counter
from pathlib import Path

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

from share import (
    AUDIO_EXTENSIONS,
    IGNORED_DIRS,
    COVER_FILENAMES,
    format_bytes,
    is_lrc_synced,
    has_embedded_cover_fast,
)

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
MAGENTA = "\033[1;35m"
CYAN = "\033[1;36m"
RED = "\033[1;31m"
DIM = "\033[2m"
RESET = "\033[0m"


def make_bar(percent, width=20, fill_color=GREEN):
    filled = int(round(width * (percent / 100.0)))
    empty = width - filled
    return f"{fill_color}{'█' * filled}{DIM}{'░' * empty}{RESET} {percent:5.1f}%"


def analyze_library(root_dir):
    root_path = os.path.abspath(root_dir)
    if not os.path.exists(root_path):
        print(f"{RED}❌ Error: Path does not exist: {root_path}{RESET}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}📊 Analyzing music library at: {root_path}...{RESET}\n")

    total_audio_files = 0
    total_audio_bytes = 0
    zero_byte_count = 0

    format_counts = Counter()
    format_sizes = Counter()

    album_dirs = defaultdict(list)
    tracks_meta = []

    unique_artists_tags = set()
    unique_albumartists_tags = set()
    unique_albums_tags = set()

    missing_artist_count = 0
    missing_album_count = 0
    missing_albumartist_count = 0
    missing_title_count = 0

    tracks_with_embedded_cover = 0
    albums_with_standalone_cover = 0
    albums_with_embedded_only = 0
    albums_with_no_cover = 0

    lrc_total = 0
    lrc_synced = 0
    lrc_unsynced = 0

    flac_hires_count = 0
    flac_16bit_count = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]

        # Check standalone cover image in this directory
        has_standalone = any(os.path.isfile(os.path.join(dirpath, cn)) and os.path.getsize(os.path.join(dirpath, cn)) > 0 for cn in COVER_FILENAMES)

        dir_audio = []
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                full_path = os.path.join(dirpath, f)
                dir_audio.append((full_path, ext))

        if dir_audio:
            album_dirs[dirpath] = (dir_audio, has_standalone)

    # Process each album directory
    for dirpath, (dir_audio, has_standalone) in album_dirs.items():
        if has_standalone:
            albums_with_standalone_cover += 1

        album_has_embed = False

        for full_path, ext in dir_audio:
            total_audio_files += 1
            try:
                sz = os.path.getsize(full_path)
            except OSError:
                sz = 0

            if sz == 0:
                zero_byte_count += 1
                continue

            total_audio_bytes += sz
            format_counts[ext] += 1
            format_sizes[ext] += sz

            # Check LRC
            lrc_path = os.path.splitext(full_path)[0] + '.lrc'
            if os.path.isfile(lrc_path) and os.path.getsize(lrc_path) > 0:
                lrc_total += 1
                if is_lrc_synced(lrc_path):
                    lrc_synced += 1
                else:
                    lrc_unsynced += 1

            # Read audio tags
            try:
                audio = mutagen.File(full_path)
                if audio is not None:
                    # Cover embed check
                    if has_embedded_cover_fast(audio, ext):
                        tracks_with_embedded_cover += 1
                        album_has_embed = True

                    # FLAC bit depth
                    if ext == '.flac' and hasattr(audio.info, 'bits_per_sample'):
                        if audio.info.bits_per_sample > 16:
                            flac_hires_count += 1
                        else:
                            flac_16bit_count += 1

                    artist, album, albumartist, title = '', '', '', ''
                    if ext == '.mp3':
                        tags = getattr(audio, 'tags', None)
                        if tags:
                            if 'TPE1' in tags: artist = str(tags['TPE1'].text[0]).strip()
                            if 'TALB' in tags: album = str(tags['TALB'].text[0]).strip()
                            if 'TPE2' in tags: albumartist = str(tags['TPE2'].text[0]).strip()
                            if 'TIT2' in tags: title = str(tags['TIT2'].text[0]).strip()
                    elif ext == '.m4a':
                        tags = getattr(audio, 'tags', None)
                        if tags:
                            if '\xa9ART' in tags: artist = str(tags['\xa9ART'][0]).strip()
                            if '\xa9alb' in tags: album = str(tags['\xa9alb'][0]).strip()
                            if 'aART' in tags: albumartist = str(tags['aART'][0]).strip()
                            if '\xa9nam' in tags: title = str(tags['\xa9nam'][0]).strip()
                    elif ext in ('.flac', '.ogg', '.opus'):
                        tags = getattr(audio, 'tags', None) or audio
                        if tags:
                            artist = str(tags.get('artist', [''])[0]).strip()
                            album = str(tags.get('album', [''])[0]).strip()
                            albumartist = str(tags.get('albumartist', tags.get('album artist', tags.get('ALBUMARTIST', tags.get('ALBUM ARTIST', ['']))))[0]).strip()
                            title = str(tags.get('title', [''])[0]).strip()

                    if artist: unique_artists_tags.add(artist)
                    else: missing_artist_count += 1

                    if album: unique_albums_tags.add(album)
                    else: missing_album_count += 1

                    if albumartist: unique_albumartists_tags.add(albumartist)
                    else: missing_albumartist_count += 1

                    if not title: missing_title_count += 1

                else:
                    missing_artist_count += 1
                    missing_album_count += 1
                    missing_albumartist_count += 1
            except Exception:
                missing_artist_count += 1

        if not has_standalone:
            if album_has_embed:
                albums_with_embedded_only += 1
            else:
                albums_with_no_cover += 1

    # Playlists count
    playlist_count = 0
    playlist_tracks = 0
    playlist_dirs = [
        root_path,
        os.path.join(root_path, 'Playlists'),
        os.path.join(os.path.dirname(root_path), 'Playlists')
    ]
    seen_pls = set()
    for pd in playlist_dirs:
        if os.path.isdir(pd):
            for pl_file in os.listdir(pd):
                if pl_file.lower().endswith(('.m3u8', '.m3u')):
                    full_pl = os.path.join(pd, pl_file)
                    if full_pl not in seen_pls:
                        seen_pls.add(full_pl)
                        playlist_count += 1
                        try:
                            with open(full_pl, 'r', encoding='utf-8', errors='ignore') as f:
                                playlist_tracks += sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
                        except Exception:
                            pass

    # Disk Space Check
    statvfs = os.statvfs(root_path)
    free_bytes = statvfs.f_bavail * statvfs.f_frsize
    total_disk_bytes = statvfs.f_blocks * statvfs.f_frsize
    used_disk_bytes = total_disk_bytes - free_bytes
    used_pct = (used_disk_bytes / total_disk_bytes) * 100 if total_disk_bytes else 0

    # Lossless vs Lossy
    lossless_count = format_counts['.flac'] + format_counts['.wav']
    lossy_count = total_audio_files - lossless_count
    lossless_pct = (lossless_count / total_audio_files * 100) if total_audio_files else 0

    # Lyrics percentages
    lyrics_pct = (lrc_total / total_audio_files * 100) if total_audio_files else 0
    synced_pct = (lrc_synced / lrc_total * 100) if lrc_total else 0

    # Total albums count
    total_albums_folders = len(album_dirs)

    # OUTPUT DASHBOARD
    print("=" * 66)
    print(f" {BOLD}{CYAN}🎶 MUSIC LIBRARY STATUS & ANALYTICS REPORT{RESET}")
    print("=" * 66)
    print(f" 📂 Root Path:        {BOLD}{root_path}{RESET}")
    print(f" 💾 Disk Usage:       {format_bytes(used_disk_bytes)} used / {format_bytes(total_disk_bytes)} total ({format_bytes(free_bytes)} free)")
    print(f"    Disk Fill:        {make_bar(used_pct, 24, BLUE)}")
    print(f" 🎵 Audio Size:       {BOLD}{format_bytes(total_audio_bytes)}{RESET} across {total_audio_files:,} tracks")
    print("-" * 66)

    # 1. Overview counts
    print(f" {BOLD}📁 Structural Totals:{RESET}")
    print(f"    • Total Tracks:         {BOLD}{total_audio_files:,}{RESET}")
    print(f"    • Album Folders:        {BOLD}{total_albums_folders:,}{RESET} (Tagged Albums: {len(unique_albums_tags):,})")
    print(f"    • Unique Artists:       {BOLD}{len(unique_artists_tags):,}{RESET} (Album Artists: {len(unique_albumartists_tags):,})")
    print(f"    • Playlists:            {BOLD}{playlist_count}{RESET} ({playlist_tracks:,} track entries)")
    print("")

    # 2. Audio Formats & Quality
    print(f" {BOLD}🎧 Audio Formats & Quality:{RESET}")
    print(f"    • Lossless (FLAC/WAV):  {BOLD}{lossless_count:,}{RESET} tracks ({lossless_pct:.1f}%)")
    if flac_hires_count > 0:
        print(f"      - Hi-Res FLAC (24-bit): {BOLD}{flac_hires_count:,}{RESET} tracks")
        print(f"      - Standard FLAC (16-bit): {flac_16bit_count:,} tracks")
    print(f"    • Lossy (M4A/MP3/OGG):  {lossy_count:,} tracks ({100 - lossless_pct:.1f}%)")
    print("")
    for ext, count in format_counts.most_common():
        pct = (count / total_audio_files) * 100
        sz_str = format_bytes(format_sizes[ext])
        ext_upper = ext[1:].upper()
        print(f"    [{ext_upper:4}] {count:5,} tracks ({pct:4.1f}%) | {sz_str:>9} | {make_bar(pct, 16, CYAN)}")
    print("")

    # 3. Cover Art Health
    print(f" {BOLD}🖼️ Cover Art Status (Rockbox Optimization):{RESET}")
    opt_albums_pct = (albums_with_standalone_cover / total_albums_folders * 100) if total_albums_folders else 0
    print(f"    • Standalone cover.jpg: {BOLD}{albums_with_standalone_cover:,} / {total_albums_folders:,}{RESET} albums {make_bar(opt_albums_pct, 16, GREEN)}")
    if tracks_with_embedded_cover == 0:
        print(f"    • Embedded Art:         {GREEN}✅ 0 tracks with embeds{RESET} (100% Rockbox Optimized!)")
    else:
        print(f"    • Embedded Art:         {YELLOW}⚠️ {tracks_with_embedded_cover:,} track(s) still contain embedded artwork{RESET}")
    if albums_with_no_cover > 0:
        print(f"    • Missing Covers:       {RED}⚠️ {albums_with_no_cover} album(s) without any cover{RESET}")
    print("")

    # 4. Lyrics (.lrc)
    print(f" {BOLD}📝 Lyrics Coverage (.lrc):{RESET}")
    print(f"    • Total Lyrics:         {BOLD}{lrc_total:,} / {total_audio_files:,}{RESET} tracks {make_bar(lyrics_pct, 16, MAGENTA)}")
    print(f"      - Synced ([mm:ss]):   {BOLD}{lrc_synced:,}{RESET} ({synced_pct:.1f}% of lyrics)")
    print(f"      - Plain Text:         {lrc_unsynced:,} ({100 - synced_pct:.1f}% of lyrics)")
    missing_lrc = total_audio_files - lrc_total
    if missing_lrc > 0:
        print(f"      - Missing Lyrics:     {missing_lrc:,} tracks")
    print("")

    # 5. Metadata Integrity for Rockbox Database
    print(f" {BOLD}🏷️ Rockbox Tag Integrity:{RESET}")
    tag_errors = 0
    if missing_albumartist_count == 0:
        print(f"    • Album Artist:         {GREEN}✅ 100% present (Prevents Split Albums!){RESET}")
    else:
        print(f"    • Album Artist:         {YELLOW}⚠️ {missing_albumartist_count:,} track(s) missing ALBUMARTIST{RESET} (May cause split albums)")
        tag_errors += 1

    if missing_album_count == 0:
        print(f"    • Album Tag:            {GREEN}✅ 100% present{RESET}")
    else:
        print(f"    • Album Tag:            {RED}⚠️ {missing_album_count:,} track(s) missing ALBUM{RESET} (Becomes <untagged>)")
        tag_errors += 1

    if missing_artist_count == 0:
        print(f"    • Artist Tag:           {GREEN}✅ 100% present{RESET}")
    else:
        print(f"    • Artist Tag:           {RED}⚠️ {missing_artist_count:,} track(s) missing ARTIST{RESET}")
        tag_errors += 1

    if zero_byte_count == 0:
        print(f"    • 0-byte Ghost Files:   {GREEN}✅ 0 files (Clean){RESET}")
    else:
        print(f"    • 0-byte Ghost Files:   {RED}⚠️ {zero_byte_count} empty file(s) found{RESET} (Triggers <untagged> in Rockbox)")
        tag_errors += 1

    print("=" * 66)
    if tag_errors == 0 and tracks_with_embedded_cover == 0:
        print(f" {GREEN}{BOLD}🎉 Your library is in pristine condition for Rockbox & DAP playback!{RESET}")
    else:
        print(f" {YELLOW}💡 Tip: Run './syncdap --optimize -r \"{root_path}\"' to optimize and fix all issues.{RESET}")
    print("=" * 66 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze audio library statistics and health for Rockbox/DAP.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music directory (default: .)")
    args = parser.parse_args()

    analyze_library(args.root_dir)


if __name__ == "__main__":
    main()
