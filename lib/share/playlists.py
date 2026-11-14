# ==============================================================================
# Module: lib/share/playlists.py
# Purpose: Shared playlist discovery, track resolution, and relative path formatting
# ==============================================================================

import os
from .constants import AUDIO_EXTENSIONS


def get_default_playlist_dir() -> str:
    """Determine standard playlist directory (preferring ../Playlists, then Playlists)."""
    if os.path.isdir('../Playlists'):
        return os.path.abspath('../Playlists')
    if os.path.isdir('Playlists'):
        return os.path.abspath('Playlists')
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl):
        return home_pl
    try:
        os.makedirs('../Playlists', exist_ok=True)
        return os.path.abspath('../Playlists')
    except Exception:
        os.makedirs('Playlists', exist_ok=True)
        return os.path.abspath('Playlists')


def find_playlist_file(query: str) -> str | None:
    """Find a playlist file matching query in standard candidate locations."""
    if not query:
        return None

    query_clean = query.strip()
    if os.path.isfile(query_clean) and query_clean.lower().endswith(('.m3u', '.m3u8')):
        return os.path.abspath(query_clean)

    candidate_dirs = []
    if os.path.isdir('../Playlists'):
        candidate_dirs.append(os.path.abspath('../Playlists'))
    if os.path.isdir('Playlists'):
        candidate_dirs.append(os.path.abspath('Playlists'))
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl) and home_pl not in candidate_dirs:
        candidate_dirs.append(home_pl)

    for d in candidate_dirs:
        for ext in ['', '.m3u8', '.m3u']:
            candidate = os.path.join(d, query_clean + ext)
            if os.path.isfile(candidate):
                return candidate
        for f in os.listdir(d):
            if f.lower().endswith(('.m3u8', '.m3u')):
                base = os.path.splitext(f)[0]
                if f.lower() == query_clean.lower() or base.strip().lower() == query_clean.lower():
                    return os.path.join(d, f)
        matches = [
            os.path.join(d, f) for f in os.listdir(d)
            if f.lower().endswith(('.m3u8', '.m3u')) and query_clean.lower() in f.lower()
        ]
        if len(matches) == 1:
            return matches[0]

    return None


def get_all_playlist_files(search_roots: list[str] | None = None) -> list[str]:
    """Retrieve all playlist files across candidate directories or provided roots."""
    candidate_dirs = []
    if search_roots:
        for r in search_roots:
            if r and os.path.exists(r):
                candidate_dirs.extend([
                    os.path.abspath(r),
                    os.path.join(os.path.abspath(r), 'Playlists'),
                    os.path.join(os.path.abspath(r), 'playlists'),
                    os.path.join(os.path.dirname(os.path.abspath(r)), 'Playlists'),
                ])
    else:
        if os.path.isdir('../Playlists'):
            candidate_dirs.append(os.path.abspath('../Playlists'))
        if os.path.isdir('Playlists'):
            candidate_dirs.append(os.path.abspath('Playlists'))
        home_pl = os.path.expanduser('~/Playlists')
        if os.path.isdir(home_pl):
            candidate_dirs.append(home_pl)

    seen = set()
    result = []
    for d in candidate_dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(('.m3u8', '.m3u')):
                p = os.path.abspath(os.path.join(d, f))
                if p not in seen:
                    seen.add(p)
                    result.append(p)
    return result


def resolve_track_file(raw_entry: str, pl_dir: str) -> str:
    """
    Resolve raw playlist line to absolute track file on disk.
    Tries relative paths, DAP root prefixes, and alternative audio extensions.
    """
    clean_entry = raw_entry.strip()
    if clean_entry.startswith('/sdcard/'):
        clean_entry = clean_entry[8:]
    elif clean_entry.startswith('sdcard/'):
        clean_entry = clean_entry[7:]

    exact_path = os.path.normpath(os.path.join(pl_dir, clean_entry))
    if os.path.isfile(exact_path):
        return exact_path

    dap_root = os.path.dirname(pl_dir)
    dap_path = os.path.normpath(os.path.join(dap_root, clean_entry))
    if os.path.isfile(dap_path):
        return dap_path

    stem, _ = os.path.splitext(exact_path)
    for ext in AUDIO_EXTENSIONS:
        candidate = stem + ext
        if os.path.isfile(candidate):
            return candidate

    return exact_path


def format_track_for_playlist(track_path: str, pl_path: str) -> str:
    """Format an audio file path as relative to the playlist directory."""
    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    track_abs = os.path.abspath(track_path)
    return os.path.relpath(track_abs, pl_dir)
