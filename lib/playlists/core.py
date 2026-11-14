# ==============================================================================
# Module: lib/playlists/core.py
# Purpose: Playlist path resolution, track analysis, and relative formatting
# ==============================================================================

import os

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')


def get_default_playlist_dir():
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


def find_playlist_file(query):
    """Find a playlist file matching query in standard locations."""
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
        matches = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(('.m3u8', '.m3u')) and query_clean.lower() in f.lower()]
        if len(matches) == 1:
            return matches[0]

    return None


def get_all_playlist_files():
    """Retrieve all playlist files across standard candidate directories."""
    candidate_dirs = []
    if os.path.isdir('../Playlists'):
        candidate_dirs.append(os.path.abspath('../Playlists'))
    if os.path.isdir('Playlists'):
        candidate_dirs.append(os.path.abspath('Playlists'))
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl) and home_pl not in candidate_dirs:
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


def resolve_track_file(raw_entry, pl_dir):
    """
    Resolve raw playlist line to absolute track file on disk.
    Checks relative paths and cross-checks alternative audio extensions.
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


def format_track_for_playlist(track_path, pl_path):
    """Format an audio file path as relative to playlist directory."""
    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    track_abs = os.path.abspath(track_path)
    return os.path.relpath(track_abs, pl_dir)


def analyze_playlist(pl_path):
    """
    Analyze all tracks in a playlist, cross-referencing other playlists
    to identify shared tracks and calculating disk usage.
    """
    pl_path = os.path.abspath(pl_path)
    pl_dir = os.path.dirname(pl_path)

    raw_lines = []
    tracks = []
    with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            raw_lines.append(line)
            s = line.strip()
            if s and not s.startswith('#'):
                resolved = resolve_track_file(s, pl_dir)
                tracks.append({
                    'raw': s,
                    'path': resolved,
                    'exists': os.path.isfile(resolved),
                    'size': os.path.getsize(resolved) if os.path.isfile(resolved) else 0,
                    'lrc': (os.path.splitext(resolved)[0] + '.lrc') if os.path.isfile(os.path.splitext(resolved)[0] + '.lrc') else None,
                    'shared_with': []
                })

    all_playlists = get_all_playlist_files()
    for other_pl in all_playlists:
        if os.path.abspath(other_pl) == pl_path:
            continue
        other_dir = os.path.dirname(other_pl)
        other_name = os.path.basename(other_pl)
        try:
            with open(other_pl, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith('#'):
                        other_resolved = resolve_track_file(s, other_dir)
                        for t in tracks:
                            if t['exists'] and os.path.abspath(t['path']) == os.path.abspath(other_resolved):
                                if other_name not in t['shared_with']:
                                    t['shared_with'].append(other_name)
        except Exception:
            pass

    return raw_lines, tracks
