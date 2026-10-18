#!/usr/bin/env python3
# ==============================================================================
# Module: lib/covers.py
# Purpose: Universal cover art embedding and Rockbox optimization (MP3, FLAC, M4A, OGG)
# ==============================================================================

import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

lock = threading.Lock()
processed_albums = 0
updated_tracks = 0

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')


def find_cover_image(album_dir):
    for name in ['cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.jpeg', 'folder.png']:
        p = os.path.join(album_dir, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p
    return None


def extract_cover_from_file(file_path, out_path):
    """Extract embedded cover from audio file to disk."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC) and tag.type in (3, 0):
                        with open(out_path, 'wb') as f:
                            f.write(tag.data)
                        return True
        elif ext == '.flac':
            audio = FLAC(file_path)
            if audio.pictures:
                for pic in audio.pictures:
                    if pic.type in (3, 0):
                        with open(out_path, 'wb') as f:
                            f.write(pic.data)
                        return True
        elif ext == '.m4a':
            audio = MP4(file_path)
            covers = audio.tags.get('covr', []) if audio.tags else []
            if covers:
                with open(out_path, 'wb') as f:
                    f.write(covers[0])
                return True
    except Exception:
        pass
    return False


def embed_cover_in_file(file_path, img_data, mime_type):
    """Embed image data as front cover into an audio file."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            # Check if same front cover already exists
            for tag in list(audio.tags.values()):
                if isinstance(tag, APIC) and tag.type == 3:
                    if len(tag.data) == len(img_data):
                        return False
            # Remove existing front covers and add new
            audio.tags.delall('APIC')
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc='',
                data=img_data
            ))
            audio.save(v2_version=3)
            return True

        elif ext == '.flac':
            audio = FLAC(file_path)
            for pic in audio.pictures:
                if pic.type == 3 and len(pic.data) == len(img_data):
                    return False
            audio.clear_pictures()
            pic = Picture()
            pic.type = 3
            pic.mime = mime_type
            pic.desc = ''
            pic.data = img_data
            audio.add_picture(pic)
            audio.save()
            return True

        elif ext == '.m4a':
            audio = MP4(file_path)
            cov_format = MP4Cover.FORMAT_PNG if 'png' in mime_type else MP4Cover.FORMAT_JPEG
            if audio.tags is None:
                audio.add_tags()
            existing = audio.tags.get('covr', [])
            if existing and len(existing[0]) == len(img_data):
                return False
            audio.tags['covr'] = [MP4Cover(img_data, imageformat=cov_format)]
            audio.save()
            return True

        elif ext in ('.ogg', '.opus'):
            import base64
            pic = Picture()
            pic.type = 3
            pic.mime = mime_type
            pic.data = img_data
            pic_data = base64.b64encode(pic.write()).decode('ascii')
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            audio['metadata_block_picture'] = [pic_data]
            audio.save()
            return True

    except Exception:
        pass
    return False


def strip_covers_from_file(file_path):
    """Strip embedded images from an audio file (Rockbox DAP mode)."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags and any(isinstance(t, APIC) for t in audio.tags.values()):
                audio.tags.delall('APIC')
                audio.save(v2_version=3)
                return True
        elif ext == '.flac':
            audio = FLAC(file_path)
            if audio.pictures:
                audio.clear_pictures()
                audio.save()
                return True
        elif ext == '.m4a':
            audio = MP4(file_path)
            if audio.tags and 'covr' in audio.tags:
                del audio.tags['covr']
                audio.save()
                return True
    except Exception:
        pass
    return False


def process_embed_album(idx, total, album_dir):
    global processed_albums, updated_tracks

    audio_files = [os.path.join(album_dir, f) for f in os.listdir(album_dir)
                   if f.lower().endswith(AUDIO_EXTENSIONS)]
    if not audio_files:
        return

    cover_file = find_cover_image(album_dir)

    # If no cover file on disk, try extracting from any track
    if not cover_file:
        cover_out = os.path.join(album_dir, 'cover.jpg')
        for f in audio_files:
            if extract_cover_from_file(f, cover_out):
                cover_file = cover_out
                break

    if not cover_file:
        with lock:
            print(f"   [{idx}/{total}] ⚠️ No cover found for: {album_dir}")
        return

    mime_type = "image/png" if cover_file.lower().endswith('.png') else "image/jpeg"
    try:
        with open(cover_file, 'rb') as cf:
            img_data = cf.read()
    except Exception:
        return

    if not img_data:
        return

    album_updated = 0
    for f in audio_files:
        if embed_cover_in_file(f, img_data, mime_type):
            album_updated += 1

    with lock:
        processed_albums += 1
        updated_tracks += album_updated
        print(f"   [{idx}/{total}] 🖼️ {album_dir} ({album_updated}/{len(audio_files)} tracks embedded)")


def process_optimize_album(idx, total, album_dir):
    global processed_albums, updated_tracks

    audio_files = [os.path.join(album_dir, f) for f in os.listdir(album_dir)
                   if f.lower().endswith(AUDIO_EXTENSIONS)]
    if not audio_files:
        return

    # Ensure cover.jpg exists first
    cover_file = find_cover_image(album_dir)
    if not cover_file:
        cover_out = os.path.join(album_dir, 'cover.jpg')
        for f in audio_files:
            if extract_cover_from_file(f, cover_out):
                cover_file = cover_out
                break

    album_stripped = 0
    for f in audio_files:
        if strip_covers_from_file(f):
            album_stripped += 1

    with lock:
        processed_albums += 1
        updated_tracks += album_stripped
        print(f"   [{idx}/{total}] 🪓 {album_dir} ({album_stripped}/{len(audio_files)} tracks stripped)")


def main():
    if len(sys.argv) < 3:
        print("Usage: covers.py <mode:embed|optimize> <dirs_file> [threads]")
        sys.exit(1)

    mode = sys.argv[1].lower()
    dirs_file = sys.argv[2]
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    album_dirs = []
    if os.path.exists(dirs_file):
        with open(dirs_file, 'r', encoding='utf-8') as f:
            album_dirs = [line.strip() for line in f if line.strip() and os.path.isdir(line.strip())]

    total = len(album_dirs)
    if total == 0:
        print("   ℹ️ No album folders found to process.")
        sys.exit(0)

    action_label = "Embedding cover arts" if mode == "embed" else "Stripping embedded APIC tags (Rockbox mode)"
    print(f"   {action_label} across {total} album(s) using {threads} worker(s)...")

    worker_fn = process_embed_album if mode == "embed" else process_optimize_album

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(worker_fn, i + 1, total, d) for i, d in enumerate(album_dirs)]
        for f in futures:
            f.result()

    summary_label = "embedded" if mode == "embed" else "optimized (stripped)"
    print(f"\n   📊 Cover art operation completed: {processed_albums} albums processed, {updated_tracks} tracks {summary_label}.")


if __name__ == '__main__':
    main()
