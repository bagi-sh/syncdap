#!/usr/bin/env python3
# ==============================================================================
# Module: lib/patch.py (formerly lib/upgrade.py)
# Purpose: Patch library or playlist tracks to another audio format (e.g. MP3 -> FLAC)
#          with safe atomic verification, tag preservation, missing track handling,
#          and playlist updates.
# ==============================================================================

import sys
import os
import re
import uuid
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, TCON, APIC, COMM, WOAS
from mutagen.mp4 import MP4, MP4Cover

# Import playlist helper functions
try:
    from playlist_ops import find_playlist_file, resolve_track_file
except ImportError:
    # If called from root directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from playlist_ops import find_playlist_file, resolve_track_file

lock = threading.Lock()
upgraded_count = 0
skipped_count = 0
failed_count = 0

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')


def extract_metadata_from_file(file_path):
    """Extract all relevant metadata, source URLs, and cover data from an existing audio file."""
    ext = os.path.splitext(file_path)[1].lower()
    meta = {
        'artist': '',
        'title': '',
        'album': '',
        'track_num': '',
        'tracks_count': '',
        'year': '',
        'genre': '',
        'spotify_url': '',
        'youtube_url': '',
        'cover_data': None,
        'cover_mime': 'image/jpeg'
    }

    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                for k, v in audio.tags.items():
                    if 'WOAS' in k:
                        meta['spotify_url'] = getattr(v, 'url', str(v)).strip()
                    elif 'COMM' in k:
                        txt = str(getattr(v, 'text', [''])[0])
                        if 'youtube.com' in txt or 'youtu.be' in txt:
                            meta['youtube_url'] = txt.strip()
                    elif isinstance(v, APIC) and v.type in (3, 0) and not meta['cover_data']:
                        meta['cover_data'] = v.data
                        meta['cover_mime'] = v.mime or 'image/jpeg'

                if 'TIT2' in audio.tags:
                    meta['title'] = str(audio.tags['TIT2'].text[0])
                if 'TPE1' in audio.tags:
                    meta['artist'] = str(audio.tags['TPE1'].text[0])
                if 'TALB' in audio.tags:
                    meta['album'] = str(audio.tags['TALB'].text[0])
                if 'TCON' in audio.tags:
                    meta['genre'] = str(audio.tags['TCON'].text[0])
                if 'TDRC' in audio.tags:
                    meta['year'] = str(audio.tags['TDRC'].text[0])[:4]
                if 'TRCK' in audio.tags:
                    tr = str(audio.tags['TRCK'].text[0]).split('/')
                    meta['track_num'] = tr[0]
                    if len(tr) > 1:
                        meta['tracks_count'] = tr[1]

        else:
            m = mutagen.File(file_path)
            if m and m.tags:
                meta['title'] = str(m.tags.get('title', [''])[0])
                meta['artist'] = str(m.tags.get('artist', [''])[0])
                meta['album'] = str(m.tags.get('album', [''])[0])
                meta['genre'] = str(m.tags.get('genre', [''])[0])
                meta['year'] = str(m.tags.get('date', [''])[0])[:4]
                meta['track_num'] = str(m.tags.get('tracknumber', [''])[0])

    except Exception:
        pass

    # Fallback to parsing filename if title/artist are missing
    if not meta['title'] or not meta['artist']:
        base = os.path.splitext(os.path.basename(file_path))[0]
        if ' - ' in base:
            parts = base.split(' - ')
            meta['artist'] = parts[-1].strip()
            title_part = ' - '.join(parts[:-1]).strip()
            if ' ' in title_part and title_part.split(' ')[0].isdigit():
                meta['track_num'] = title_part.split(' ')[0]
                meta['title'] = ' '.join(title_part.split(' ')[1:]).strip()
            else:
                meta['title'] = title_part

    # Fallback album name from directory
    if not meta['album']:
        parent = os.path.basename(os.path.dirname(os.path.abspath(file_path)))
        if parent and parent != '.':
            meta['album'] = parent

    return meta


def transfer_tags_to_file(dest_file, meta, cover_path=None):
    """Write preserved metadata and cover art into the newly downloaded audio file."""
    ext = os.path.splitext(dest_file)[1].lower()

    # Load cover image data
    img_data = meta['cover_data']
    mime_type = meta['cover_mime']
    if not img_data and cover_path and os.path.isfile(cover_path):
        try:
            with open(cover_path, 'rb') as f:
                img_data = f.read()
            mime_type = 'image/png' if cover_path.lower().endswith('.png') else 'image/jpeg'
        except Exception:
            pass

    try:
        if ext == '.flac':
            audio = FLAC(dest_file)
            if meta['title']:
                audio['title'] = meta['title']
            if meta['artist']:
                audio['artist'] = meta['artist']
            if meta['album']:
                audio['album'] = meta['album']
            if meta['year']:
                audio['date'] = str(meta['year'])
            if meta['genre']:
                audio['genre'] = meta['genre']
            if meta['track_num']:
                audio['tracknumber'] = str(meta['track_num'])
            if meta['tracks_count']:
                audio['totaltracks'] = str(meta['tracks_count'])

            if img_data:
                pic = Picture()
                pic.data = img_data
                pic.type = 3  # Cover (front)
                pic.mime = mime_type
                audio.clear_pictures()
                audio.add_picture(pic)
            audio.save()

        elif ext == '.mp3':
            audio = MP3(dest_file, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
            if meta['title']:
                tags.setall('TIT2', [TIT2(encoding=3, text=meta['title'])])
            if meta['artist']:
                tags.setall('TPE1', [TPE1(encoding=3, text=meta['artist'])])
            if meta['album']:
                tags.setall('TALB', [TALB(encoding=3, text=meta['album'])])
            if meta['year']:
                tags.setall('TDRC', [TDRC(encoding=3, text=str(meta['year']))])
            if meta['genre']:
                tags.setall('TCON', [TCON(encoding=3, text=meta['genre'])])
            if meta['track_num']:
                tr_str = f"{meta['track_num']}/{meta['tracks_count']}" if meta['tracks_count'] else str(meta['track_num'])
                tags.setall('TRCK', [TRCK(encoding=3, text=tr_str)])

            if img_data:
                tags.delall('APIC')
                tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=img_data
                ))
            audio.save(v2_version=3)

        elif ext == '.m4a':
            audio = MP4(dest_file)
            if audio.tags is None:
                audio.add_tags()
            if meta['title']:
                audio.tags['\xa9nam'] = [meta['title']]
            if meta['artist']:
                audio.tags['\xa9ART'] = [meta['artist']]
            if meta['album']:
                audio.tags['\xa9alb'] = [meta['album']]
            if meta['year']:
                audio.tags['\xa9day'] = [str(meta['year'])]
            if meta['genre']:
                audio.tags['\xa9gen'] = [str(meta['genre'])]
            if meta['track_num']:
                t_num = int(meta['track_num']) if str(meta['track_num']).isdigit() else 1
                t_tot = int(meta['tracks_count']) if str(meta['tracks_count']).isdigit() else 0
                audio.tags['trkn'] = [(t_num, t_tot)]
            if img_data:
                cov_fmt = MP4Cover.FORMAT_PNG if 'png' in mime_type else MP4Cover.FORMAT_JPEG
                audio.tags['covr'] = [MP4Cover(img_data, imageformat=cov_fmt)]
            audio.save()

    except Exception:
        pass


def update_playlists(old_rel_path, new_rel_path):
    """Replace references from old_rel_path to new_rel_path in all .m3u8 and .m3u files."""
    candidate_dirs = []
    if os.path.isdir('../Playlists'):
        candidate_dirs.append('../Playlists')
    if os.path.isdir('Playlists'):
        candidate_dirs.append('Playlists')
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl) and os.path.abspath(home_pl) not in [os.path.abspath(d) for d in candidate_dirs]:
        candidate_dirs.append(home_pl)

    if not candidate_dirs:
        return

    old_norm = os.path.normpath(old_rel_path)
    new_norm = os.path.normpath(new_rel_path)

    for pdir in candidate_dirs:
        for pfile in os.listdir(pdir):
            if pfile.lower().endswith(('.m3u8', '.m3u')):
                pl_path = os.path.join(pdir, pfile)
                try:
                    with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    changed = False
                    # Check ../Music/ prefix first
                    if f"../Music/{old_norm}" in content:
                        content = content.replace(f"../Music/{old_norm}", f"../Music/{new_norm}")
                        changed = True
                    # Check ../ prefix
                    if f"../{old_norm}" in content:
                        content = content.replace(f"../{old_norm}", f"../{new_norm}")
                        changed = True
                    # Check exact relative prefix
                    if old_norm in content:
                        content = content.replace(old_norm, new_norm)
                        changed = True

                    if changed:
                        with open(pl_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                except Exception:
                    pass


def upgrade_track(idx, total, old_file, target_format, keep_old, dry_run, temp_dir, js_args):
    global upgraded_count, skipped_count, failed_count

    target_ext = f".{target_format}"
    base_no_ext, old_ext = os.path.splitext(old_file)
    new_file = f"{base_no_ext}{target_ext}"

    if old_ext.lower() == target_ext.lower():
        with lock:
            skipped_count += 1
            print(f"   [{idx}/{total}] ⏩ Already in {target_format.upper()}: {old_file}")
        return True

    meta = extract_metadata_from_file(old_file)
    artist = meta['artist']
    title = meta['title']
    album = meta['album']
    spotify_url = meta['spotify_url']
    youtube_url = meta['youtube_url']

    with lock:
        label = f"{artist} - {title}" if artist and title else os.path.basename(old_file)
        print(f"   [{idx}/{total}] 🔄 Patching: {label} ({old_ext.upper()[1:]} -> {target_format.upper()})")

    if dry_run:
        with lock:
            upgraded_count += 1
            print(f"   [{idx}/{total}] 🔍 [DRY-RUN] Would download and replace: {old_file} -> {new_file}")
        return True

    temp_id = uuid.uuid4().hex
    temp_target = os.path.join(temp_dir, f"patch_{temp_id}.{target_format}")
    ytdlp_fmt = 'vorbis' if target_format == 'ogg' else target_format

    success = False

    # Strategy 1: Exact YouTube stream URL if stored in comments
    if youtube_url and not success:
        cmd = [
            'yt-dlp', youtube_url,
            '--no-playlist',
            *js_args,
            '-x', '--audio-format', ytdlp_fmt,
            '--audio-quality', '0',
            '-o', f"{os.path.join(temp_dir, f'patch_{temp_id}')}.%(ext)s"
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.isfile(temp_target) and os.path.getsize(temp_target) > 2048:
            success = True

    # Strategy 2: Official Spotify URL via spotdl
    if spotify_url and not success:
        bitrate_arg = 'auto' if target_format in ('flac', 'wav') else '320k'
        cmd = [
            'spotdl', 'download', spotify_url,
            '--format', target_format,
            '--bitrate', bitrate_arg,
            '--output', os.path.join(temp_dir, f"patch_{temp_id}.{{output-ext}}"),
            '--max-retries', '1'
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.isfile(temp_target) and os.path.getsize(temp_target) > 2048:
            success = True

    # Strategy 3: Search fallback via yt-dlp
    if not success and artist and title:
        search_query = f"ytsearch1:{artist} - {title}"
        if album:
            search_query += f" {album}"
        cmd = [
            'yt-dlp', search_query,
            '--no-playlist',
            *js_args,
            '-x', '--audio-format', ytdlp_fmt,
            '--audio-quality', '0',
            '-o', f"{os.path.join(temp_dir, f'patch_{temp_id}')}.%(ext)s"
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.isfile(temp_target) and os.path.getsize(temp_target) > 2048:
            success = True

    # Validation: Audio integrity check
    if success:
        try:
            test_audio = mutagen.File(temp_target)
            if test_audio is None or getattr(test_audio.info, 'length', 0) <= 0:
                success = False
        except Exception:
            success = False

    if not success:
        if os.path.isfile(temp_target):
            try:
                os.remove(temp_target)
            except Exception:
                pass
        with lock:
            failed_count += 1
            print(f"   [{idx}/{total}] ❌ Failed to download or validate {target_format.upper()} for: {label}")
            print(f"      🛡️ Safety: Original file kept intact: {old_file}")
        return False

    # Transfer tags and cover art
    album_dir = os.path.dirname(os.path.abspath(old_file))
    cover_jpg = os.path.join(album_dir, 'cover.jpg')
    transfer_tags_to_file(temp_target, meta, cover_path=cover_jpg)

    # Safely move new file into destination
    try:
        shutil.move(temp_target, new_file)
    except Exception as e:
        with lock:
            failed_count += 1
            print(f"   [{idx}/{total}] ❌ Could not place {new_file}: {e}")
        return False

    if os.path.isfile(new_file) and os.path.getsize(new_file) > 2048:
        # Preserve matching .lrc lyrics file if present
        old_lrc = f"{base_no_ext}.lrc"
        new_lrc = f"{base_no_ext}.lrc"
        if os.path.isfile(old_lrc) and old_lrc != new_lrc:
            try:
                shutil.copy2(old_lrc, new_lrc)
            except Exception:
                pass

        # Update all playlist references
        update_playlists(old_file, new_file)

        # Remove old file only if not keep_old
        if not keep_old and os.path.abspath(old_file) != os.path.abspath(new_file):
            try:
                os.remove(old_file)
            except Exception as e:
                with lock:
                    print(f"      ⚠️ Warning: Could not remove old file {old_file}: {e}")

        with lock:
            upgraded_count += 1
            status_note = "replaced" if not keep_old else "kept old alongside"
            print(f"   [{idx}/{total}] ✅ Patched ({status_note}): {new_file}")
        return True
    else:
        with lock:
            failed_count += 1
            print(f"   [{idx}/{total}] ❌ Unexpected error finalizing {new_file}. Keeping {old_file}")
        return False


def handle_playlist_patch(pl_path, target_format, keep_old, dry_run, temp_dir, js_args, threads, assume_yes):
    """Scan and patch tracks referenced by a specific playlist file."""
    print(f"\n📋 Playlist mode: Inspecting entries in '{os.path.basename(pl_path)}'...")
    pl_dir = os.path.dirname(os.path.abspath(pl_path))

    target_ext = f".{target_format.lower()}"
    files_to_upgrade = []

    lines_to_remove = set()
    album_clean_decisions = {}
    artist_clean_decisions = {}
    all_keep = assume_yes

    with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
        playlist_lines = f.readlines()

    for line in playlist_lines:
        s = line.strip()
        if not s or s.startswith('#'):
            continue

        resolved = resolve_track_file(s, pl_dir)
        if os.path.isfile(resolved):
            ext = os.path.splitext(resolved)[1].lower()
            if ext != target_ext:
                files_to_upgrade.append(os.path.relpath(resolved, '.'))
            else:
                print(f"   ⏩ Already in {target_format.upper()}: {os.path.basename(resolved)}")
        else:
            # Track does not exist on disk
            print(f"\n   ⚠️ Audio file for '{s}' does not exist on disk.")
            track_album = os.path.dirname(os.path.abspath(resolved))
            track_artist = os.path.dirname(track_album)

            remove_entry = False
            if all_keep:
                remove_entry = False
            elif track_artist in artist_clean_decisions:
                remove_entry = artist_clean_decisions[track_artist]
            elif track_album in album_clean_decisions:
                remove_entry = album_clean_decisions[track_album]
            else:
                print(f"      Expected folder: {track_album}")
                print("      Options: [y] Remove from playlist | [n] Keep in playlist | [a] Entire album | [r] Entire artist | [k] Keep all remaining")
                ans = input("      Remove this entry from the playlist? [y/N]: ").strip().lower()

                if ans in ('y', 'yes', 's', 'sim'):
                    remove_entry = True
                elif ans in ('a', 'album'):
                    album_clean_decisions[track_album] = True
                    remove_entry = True
                elif ans in ('r', 'artist', 'artista'):
                    artist_clean_decisions[track_artist] = True
                    remove_entry = True
                elif ans in ('k', 'keep', 't', 'all'):
                    all_keep = True
                    remove_entry = False
                else:
                    remove_entry = False

            if remove_entry:
                lines_to_remove.add(line)

    # Clean removed lines from playlist if any
    if lines_to_remove:
        new_lines = [l for l in playlist_lines if l not in lines_to_remove]
        with open(pl_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"   🧹 {len(lines_to_remove)} missing entry(ies) removed from '{os.path.basename(pl_path)}'.")

    return sorted(list(set(files_to_upgrade)))


def main():
    if len(sys.argv) < 3:
        print("Usage: patch.py <target_format> <temp_dir> [threads] [keep_old] [dry_run] [filter_term] [js_args] [assume_yes]")
        sys.exit(1)

    target_format = sys.argv[1].lower()
    temp_dir = sys.argv[2]
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    keep_old = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False
    dry_run = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False
    filter_term = sys.argv[6] if len(sys.argv) > 6 else ""
    ytdlp_js_raw = sys.argv[7] if len(sys.argv) > 7 else ""
    assume_yes = sys.argv[8].lower() == 'true' if len(sys.argv) > 8 else False

    js_args = ytdlp_js_raw.split() if ytdlp_js_raw else []
    target_ext = f".{target_format}"

    files_to_upgrade = []

    # Check if filter_term is a playlist
    matched_pl = find_playlist_file(filter_term) if filter_term else None

    if matched_pl:
        files_to_upgrade = handle_playlist_patch(
            matched_pl, target_format, keep_old, dry_run, temp_dir, js_args, threads, assume_yes
        )
    else:
        # Standard library walk / filter
        for root, _, files in os.walk('.'):
            if root.startswith('./Playlists') or root == '.':
                continue
            if filter_term and filter_term.lower() not in root.lower():
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTENSIONS and ext != target_ext:
                    files_to_upgrade.append(os.path.join(root, f))

        files_to_upgrade.sort()

    total = len(files_to_upgrade)
    if total == 0:
        print(f"   ✨ No tracks requiring patch to {target_format.upper()} were found.")
        sys.exit(0)

    print(f"   Found {total} track(s) for quality patch to {target_format.upper()} using {threads} worker(s)...")
    if keep_old:
        print("   🛡️ Mode: --keep-old enabled (original files will not be deleted).")
    if dry_run:
        print("   🔍 Mode: --dry-run enabled (simulating patch without changes).")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(upgrade_track, i + 1, total, f, target_format, keep_old, dry_run, temp_dir, js_args)
                   for i, f in enumerate(files_to_upgrade)]
        for f in futures:
            f.result()

    print(f"\n   📊 Patch completed: {upgraded_count} patched, {skipped_count} skipped, {failed_count} failed out of {total}.")


if __name__ == '__main__':
    main()
