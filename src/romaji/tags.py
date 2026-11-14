# ==============================================================================
# Module: src/romaji/tags.py
# Purpose: Audio metadata tag transliteration for ID3, Vorbis, and MP4
# ==============================================================================

import threading
from pathlib import Path

import mutagen
from mutagen import File

from .translit import to_romaji

_print_lock = threading.Lock()


def process_audio_tags(filepath: Path, dry_run: bool) -> bool:
    """Update Japanese tags (Title, Artist, Album) to Romaji in audio metadata."""
    try:
        if not filepath.exists() or filepath.stat().st_size == 0:
            return False

        audio = File(filepath)
        if audio is None:
            return False

        modified = False

        # 1. ID3 (MP3)
        is_id3 = isinstance(getattr(audio, 'tags', None), mutagen.id3.ID3)
        if is_id3:
            for key in list(audio.tags.keys()):
                key_lower = key.lower()
                if any(k in key_lower for k in ['tit2', 'tpe1', 'talb', 'title', 'artist', 'album']):
                    frame = audio.tags[key]
                    if hasattr(frame, 'text'):
                        old_text = [str(t) for t in frame.text]
                        new_text = [to_romaji(t, for_filename=False, for_folder=False, for_tag=True) for t in old_text]
                        if old_text != new_text:
                            modified = True
                            with _print_lock:
                                print(f"   [ID3 TAG] {filepath.name} ({key}): {old_text} -> {new_text}")
                            if not dry_run:
                                frame.text = new_text

        # 2. FLAC, OGG, M4A, WAV (VorbisComments / MP4Tags)
        else:
            tag_dict = audio.tags if audio.tags is not None else audio
            for key in list(tag_dict.keys()):
                key_lower = key.lower()
                if any(k in key_lower for k in ['title', 'artist', 'album', 'nam', 'art', 'alb']):
                    val = tag_dict[key]
                    if isinstance(val, list):
                        new_val = [to_romaji(str(v), for_filename=False, for_folder=False, for_tag=True) for v in val]
                    else:
                        new_val = to_romaji(str(val), for_filename=False, for_folder=False, for_tag=True)

                    if str(val) != str(new_val):
                        modified = True
                        with _print_lock:
                            print(f"   [TAG] {filepath.name} ({key}): '{val}' -> '{new_val}'")
                        if not dry_run:
                            tag_dict[key] = new_val

        if modified and not dry_run:
            audio.save()
            return True

        return modified

    except Exception as e:
        with _print_lock:
            print(f"   [TAG ERROR] {filepath.name}: {e}")
        return False
