# ==============================================================================
# Module: src/patch/worker.py
# Purpose: Single track downloader, converter, and validator worker
# ==============================================================================

import os
import uuid
import shutil
import subprocess
import mutagen

from .metadata import extract_metadata_from_file, transfer_tags_to_file
from .playlist import update_playlists


def upgrade_track(idx, total, old_file, target_format, keep_old, dry_run, temp_dir, js_args, counters, lock):
    target_ext = f".{target_format}"
    base_no_ext, old_ext = os.path.splitext(old_file)
    new_file = f"{base_no_ext}{target_ext}"

    if old_ext.lower() == target_ext.lower():
        with lock:
            counters['skipped'] += 1
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
            counters['upgraded'] += 1
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
            counters['failed'] += 1
            print(f"   [{idx}/{total}] ❌ Failed to download or validate {target_format.upper()} for: {label}")
            print(f"      🛡️ Safety: Original file kept intact: {old_file}")
        return False

    album_dir = os.path.dirname(os.path.abspath(old_file))
    cover_jpg = os.path.join(album_dir, 'cover.jpg')
    transfer_tags_to_file(temp_target, meta, cover_path=cover_jpg)

    try:
        shutil.move(temp_target, new_file)
    except Exception as e:
        with lock:
            counters['failed'] += 1
            print(f"   [{idx}/{total}] ❌ Could not place {new_file}: {e}")
        return False

    if os.path.isfile(new_file) and os.path.getsize(new_file) > 2048:
        old_lrc = f"{base_no_ext}.lrc"
        new_lrc = f"{base_no_ext}.lrc"
        if os.path.isfile(old_lrc) and old_lrc != new_lrc:
            try:
                shutil.copy2(old_lrc, new_lrc)
            except Exception:
                pass

        update_playlists(old_file, new_file)

        if not keep_old and os.path.abspath(old_file) != os.path.abspath(new_file):
            try:
                os.remove(old_file)
            except Exception as e:
                with lock:
                    print(f"      ⚠️ Warning: Could not remove old file {old_file}: {e}")

        with lock:
            counters['upgraded'] += 1
            status_note = "replaced" if not keep_old else "kept old alongside"
            print(f"   [{idx}/{total}] ✅ Patched ({status_note}): {new_file}")
        return True
    else:
        with lock:
            counters['failed'] += 1
            print(f"   [{idx}/{total}] ❌ Unexpected error finalizing {new_file}. Keeping {old_file}")
        return False
