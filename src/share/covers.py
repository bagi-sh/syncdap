"""Shared cover artwork detection and frame extraction utilities."""

import os
import base64

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

from .constants import COVER_FILENAMES


def find_cover_image(album_dir: str) -> str | None:
    """Find local front cover art file in album_dir (cover.jpg, folder.jpg, etc.)."""
    if not album_dir or not os.path.isdir(album_dir):
        return None
    for name in COVER_FILENAMES:
        p = os.path.join(album_dir, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return os.path.abspath(p)
    return None


def extract_cover_from_file(file_path: str, out_path: str) -> bool:
    """Extract embedded front cover artwork from an audio file to disk."""
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


def embed_cover_in_file(file_path: str, img_data: bytes, mime_type: str = 'image/jpeg') -> bool:
    """Embed image bytes as front cover artwork into an audio file."""
    if not img_data or not os.path.isfile(file_path):
        return False
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            if audio.tags is None:
                audio.add_tags()
            for tag in list(audio.tags.values()):
                if isinstance(tag, APIC) and tag.type == 3:
                    if len(tag.data) == len(img_data):
                        return False
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
            cov_format = MP4Cover.FORMAT_PNG if 'png' in mime_type.lower() else MP4Cover.FORMAT_JPEG
            if audio.tags is None:
                audio.add_tags()
            existing = audio.tags.get('covr', [])
            if existing and len(existing[0]) == len(img_data):
                return False
            audio.tags['covr'] = [MP4Cover(img_data, imageformat=cov_format)]
            audio.save()
            return True

        elif ext in ('.ogg', '.opus'):
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


def has_embedded_cover(file_path: str) -> bool:
    """Quick check if an audio file contains embedded cover art."""
    if not file_path or not os.path.isfile(file_path):
        return False
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.mp3':
            audio = MP3(file_path, ID3=ID3)
            return bool(audio.tags and any(isinstance(t, APIC) for t in audio.tags.values()))
        elif ext == '.flac':
            audio = FLAC(file_path)
            return bool(audio.pictures)
        elif ext == '.m4a':
            audio = MP4(file_path)
            return bool(audio.tags and 'covr' in audio.tags and audio.tags['covr'])
        elif ext in ('.ogg', '.opus'):
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            return bool('metadata_block_picture' in audio or 'coverart' in audio)
    except Exception:
        pass
    return False


def strip_covers_from_file(file_path: str) -> bool:
    """Strip embedded cover artwork from an audio file (optimized for Rockbox DAPs)."""
    if not file_path or not os.path.isfile(file_path):
        return False
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
        elif ext in ('.ogg', '.opus'):
            audio = OggOpus(file_path) if ext == '.opus' else OggVorbis(file_path)
            if 'metadata_block_picture' in audio:
                del audio['metadata_block_picture']
                audio.save()
                return True
    except Exception:
        pass
    return False
