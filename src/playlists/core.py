"""Core playlist parsing, loading, and serialization utilities."""

import os
from share import (
    AUDIO_EXTENSIONS,
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
    parse_playlist_file,
)


def analyze_playlist(pl_path):
    """
    Analyze all tracks in a playlist, cross-referencing other playlists
    to identify shared tracks and calculating disk usage.
    """
    pl_path = os.path.abspath(pl_path)
    entries = parse_playlist_file(pl_path)

    raw_lines = [e.raw + '\n' for e in entries]
    tracks = []
    for e in entries:
        if not e.is_comment and e.track_path:
            tracks.append({
                'raw': e.track_path,
                'path': e.resolved_path,
                'exists': e.exists,
                'size': os.path.getsize(e.resolved_path) if e.exists else 0,
                'lrc': (os.path.splitext(e.resolved_path)[0] + '.lrc') if os.path.isfile(os.path.splitext(e.resolved_path)[0] + '.lrc') else None,
                'shared_with': []
            })

    tracks_by_path = {os.path.abspath(t['path']): t for t in tracks if t['exists']}

    all_playlists = get_all_playlist_files()
    for other_pl in all_playlists:
        if os.path.abspath(other_pl) == pl_path:
            continue
        other_name = os.path.basename(other_pl)
        try:
            other_entries = parse_playlist_file(other_pl)
            for oe in other_entries:
                if not oe.is_comment and oe.resolved_path:
                    oe_abs = os.path.abspath(oe.resolved_path)
                    matched_t = tracks_by_path.get(oe_abs)
                    if matched_t and other_name not in matched_t['shared_with']:
                        matched_t['shared_with'].append(other_name)
        except Exception:
            pass

    return raw_lines, tracks
