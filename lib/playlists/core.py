# ==============================================================================
# Module: lib/playlists/core.py
# Purpose: Playlist analysis and track relationship mapping
# ==============================================================================

import os
from share import (
    AUDIO_EXTENSIONS,
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
)


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
