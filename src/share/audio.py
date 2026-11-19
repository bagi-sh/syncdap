# ==============================================================================
# Module: src/share/audio.py
# Purpose: Shared audio file discovery, metadata extraction, cover art checks,
#          and audio quality comparison helpers
# ==============================================================================

import json
import os
import re
import subprocess

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus

from .constants import AUDIO_EXTENSIONS, IGNORED_DIRS, LOSSLESS_EXTENSIONS
from .text import clean_string


def find_audio_files(root_dir: str) -> list[str]:
    """Scan root_dir recursively for audio files excluding ignored system directories."""
    audio_files = []
    root_path = os.path.abspath(root_dir)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')
        ]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                audio_files.append(os.path.join(dirpath, f))

    return sorted(audio_files)


def get_audio_metadata(audio_path: str) -> dict:
    """Extract metadata (artist, title, album, duration, track number) using Mutagen."""
    info = {
        'artist': '',
        'title': '',
        'album': '',
        'duration': None,
        'track_num': '',
        'year': '',
        'genre': '',
    }
    try:
        audio = mutagen.File(audio_path)
        if audio is not None:
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                info['duration'] = audio.info.length

            if isinstance(getattr(audio, 'tags', None), ID3):
                tags = audio.tags
                if 'TIT2' in tags:
                    info['title'] = clean_string(tags['TIT2'].text)
                if 'TPE1' in tags:
                    info['artist'] = clean_string(tags['TPE1'].text)
                if 'TALB' in tags:
                    info['album'] = clean_string(tags['TALB'].text)
                if 'TRCK' in tags:
                    info['track_num'] = clean_string(tags['TRCK'].text).split('/')[0]
                if 'TDRC' in tags:
                    info['year'] = clean_string(tags['TDRC'].text)[:4]
                if 'TCON' in tags:
                    info['genre'] = clean_string(tags['TCON'].text)
            elif audio.tags:
                tags = audio.tags
                info['title']     = clean_string(tags.get('title',       tags.get('\xa9nam', [''])))
                info['artist']    = clean_string(tags.get('artist',      tags.get('\xa9ART', [''])))
                info['album']     = clean_string(tags.get('album',       tags.get('\xa9alb', [''])))
                info['track_num'] = clean_string(tags.get('tracknumber', tags.get('trkn',   [''])))
                info['genre']     = clean_string(tags.get('genre',       tags.get('\xa9gen', [''])))
                info['year']      = clean_string(tags.get('date',        tags.get('\xa9day', [''])))[:4]
    except Exception:
        pass

    return info


def has_embedded_cover_fast(audio, ext: str) -> bool:
    """Check whether audio object contains embedded front cover artwork."""
    try:
        if ext == '.mp3' and isinstance(audio, MP3) and audio.tags:
            for k in audio.tags.keys():
                if k.startswith('APIC'):
                    return True
        elif ext == '.flac' and isinstance(audio, FLAC):
            if bool(audio.pictures):
                return True
        elif ext == '.m4a' and isinstance(audio, MP4) and audio.tags:
            if 'covr' in audio.tags and bool(audio.tags['covr']):
                return True
        elif ext in ('.ogg', '.opus') and isinstance(audio, (OggVorbis, OggOpus)) and audio.tags:
            if 'metadata_block_picture' in audio.tags or 'coverart' in audio.tags:
                return True
    except Exception:
        pass
    return False


# ==============================================================================
# Audio quality helpers (used by split, audit, dedup)
# ==============================================================================

def get_file_duration(path: str) -> float:
    """Return duration in seconds via ffprobe (no mutagen), or 0.0 on failure."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_entries', 'format=duration', path
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        return float(json.loads(out).get('format', {}).get('duration', 0.0))
    except Exception:
        return 0.0


def is_lossless(path: str) -> bool:
    """Return True if the file extension indicates a lossless format."""
    return os.path.splitext(path)[1].lower() in LOSSLESS_EXTENSIONS


def get_bitrate_kbps(path: str) -> int:
    """Return audio bitrate in kbps via ffprobe, or 0 on failure."""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_entries', 'format=bit_rate', path
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        br = json.loads(out).get('format', {}).get('bit_rate', 0)
        return int(br) // 1000
    except Exception:
        return 0


def track_number_from_filename(fname: str) -> int | None:
    """Extract leading track number from filename (e.g. '03 Title - Artist.mp3' → 3)."""
    m = re.match(r'^(\d+)\s', fname)
    return int(m.group(1)) if m else None


def audio_quality_wins(candidate: str, incumbent: str) -> tuple[bool, str]:
    """
    Compare quality of two audio files. Returns (should_replace: bool, reason: str).
    Rules: lossless > lossy; within same category, higher bitrate wins.
    """
    cand_ll = is_lossless(candidate)
    inc_ll  = is_lossless(incumbent)

    if cand_ll and not inc_ll:
        return True,  "candidate is lossless, incumbent is lossy → upgrade"
    if not cand_ll and inc_ll:
        return False, "incumbent is lossless, candidate is lossy → keep incumbent"

    cand_br = get_bitrate_kbps(candidate)
    inc_br  = get_bitrate_kbps(incumbent)
    if cand_br > inc_br:
        return True,  f"candidate has higher bitrate ({cand_br} > {inc_br} kbps) → upgrade"
    return False, f"incumbent has same/better bitrate ({inc_br} >= {cand_br} kbps) → keep incumbent"


def is_valid_audio(path: str) -> bool:
    """Return True if path points to an existing, non-empty, playable audio file."""
    try:
        if not path or not os.path.isfile(path):
            return False
        if os.path.getsize(path) <= 0:
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext not in AUDIO_EXTENSIONS:
            return False
        dur = get_file_duration(path)
        if dur > 0:
            return True
        meta = get_audio_metadata(path)
        return bool(meta.get('duration') and meta['duration'] > 0)
    except Exception:
        return False
