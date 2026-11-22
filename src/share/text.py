"""Shared filename parsing and string sanitization for FAT32."""

import os
import re
import unicodedata

# Common symbol replacements for safe filesystem names
SYMBOL_REPLACEMENTS = {
    '℃': 'C',
    '℉': 'F',
    '＆': '&',
    '％': '%',
    '＋': '+',
    '・': ' ',
    '…': '...',
    '、': ', ',
    '。': '',
    '！': '!',
    '？': '?',
    '：': ': ',
    '　': ' ',
}


def normalize_str(s: str) -> str:
    """Normalize string for loose title/artist matching (lowercase, stripped punctuation/spaces)."""
    if not s:
        return ""
    s = str(s).lower().strip()
    s = re.sub(r'[\s_\-]+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()


def clean_string(val) -> str:
    """Clean tag value, unwrapping list/tuple if present and removing extra whitespace."""
    if not val:
        return ""
    if isinstance(val, (list, tuple)):
        val = val[0] if val else ""
    val = str(val).strip()
    return re.sub(r'\s+', ' ', val)


def clean_term(s: str) -> str:
    """Clean artist/album string by removing parentheticals and feature credits for API queries."""
    if not s:
        return ""
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'\[.*?\]', '', s)
    s = re.sub(r'feat\..*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'ft\..*', '', s, flags=re.IGNORECASE)
    return s.strip()


def sanitize_filename(name: str, for_folder: bool = False) -> str:
    """Sanitize name for FAT32 / exFAT filesystems removing illegal characters."""
    if not name:
        return name

    name = unicodedata.normalize('NFKC', str(name))

    for old_sym, new_sym in SYMBOL_REPLACEMENTS.items():
        name = name.replace(old_sym, new_sym)

    # Remove characters forbidden by FAT32 / exFAT: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/:*?"<>|]', '', name)
    sanitized = re.sub(r'\s*-\s*', ' - ', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip(' .,-_')

    return sanitized or "Unknown"


def parse_filename_metadata(file_path: str) -> dict:
    """
    Extract track number, title, artist, and album from audio filename and parent folder.
    Supports formats like '01 Title - Artist.mp3' and 'Title - Artist.flac'.
    """
    base_name = os.path.basename(file_path)
    stem, ext = os.path.splitext(base_name)
    parent_dir = os.path.dirname(os.path.abspath(file_path))
    album_dir = os.path.basename(parent_dir)
    artist_dir = os.path.basename(os.path.dirname(parent_dir))

    track_no = ""
    title = ""
    artist = ""

    # Check "01 Title - Artist" or "01 - Title - Artist"
    match = re.match(r'^(\d{1,3})\s*[-._\s]\s*(.*)$', stem)
    if match:
        track_no = str(int(match.group(1)))
        rest = match.group(2).strip()
        if ' - ' in rest:
            parts = rest.split(' - ')
            title = ' - '.join(parts[:-1]).strip()
            artist = parts[-1].strip()
        else:
            title = rest
    elif ' - ' in stem:
        parts = stem.split(' - ')
        title = ' - '.join(parts[:-1]).strip()
        artist = parts[-1].strip()
    else:
        title = stem

    return {
        'path': file_path,
        'stem': stem,
        'ext': ext.lower(),
        'parent_dir': parent_dir,
        'album_dir': album_dir,
        'artist_dir': artist_dir,
        'track_no': track_no,
        'track_num': track_no,
        'title': clean_string(title),
        'artist': clean_string(artist),
        'album': clean_string(album_dir) if album_dir != '.' else ""
    }


def parse_timestamp_to_seconds(ts_str: str) -> float | None:
    """
    Parse timestamp string into float seconds.
    Supports HH:MM:SS, MM:SS, MM:SS.ff (CUE frames), and raw seconds.
    """
    if not ts_str:
        return None
    s = ts_str.strip().strip('[]()')
    parts = s.split(':')
    try:
        if len(parts) == 3:
            # HH:MM:SS or MM:SS:FF (CUE frame format: 75 frames per second)
            # If the third part has 2 digits and first part < 100, might be MM:SS:FF
            h, m, sec = float(parts[0]), float(parts[1]), float(parts[2])
            return h * 3600.0 + m * 60.0 + sec
        elif len(parts) == 2:
            m, sec = float(parts[0]), float(parts[1])
            return m * 60.0 + sec
        elif len(parts) == 1:
            return float(parts[0])
    except (ValueError, TypeError):
        return None
    return None


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds to standard M:SS or H:MM:SS string."""
    if seconds is None or seconds < 0:
        return "--:--"
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_bytes(num_bytes: float | int) -> str:
    """Format byte size into human readable string (KB, MB, GB, TB)."""
    if num_bytes is None or num_bytes < 0:
        return "0 B"
    val = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if val < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} PB"
