# ==============================================================================
# Module: src/share/playlists.py
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


def expand_playlist_entries(root_dir: str, migration_map: dict[str, list[str]]) -> int:
    """
    Expand 1-to-N bundled album references into individual track entries across playlists.
    migration_map: { old_abs_path: [new_abs_track_01, new_abs_track_02, ...] }
    Preserves #EXTINF comments, prevents duplicates, and saves atomically.
    Returns the number of modified playlists.
    """
    if not migration_map:
        return 0

    norm_map = {
        os.path.abspath(k): [os.path.abspath(p) for p in v]
        for k, v in migration_map.items() if v
    }
    if not norm_map:
        return 0

    all_playlists = get_all_playlist_files([root_dir])
    modified_count = 0

    for pl_path in all_playlists:
        if not os.path.isfile(pl_path):
            continue

        pl_dir = os.path.dirname(os.path.abspath(pl_path))
        try:
            with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            continue

        new_lines: list[str] = []
        changed = False
        seen_tracks = set()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue

            if stripped.startswith('#'):
                new_lines.append(line)
                continue

            resolved = resolve_track_file(stripped, pl_dir)
            abs_resolved = os.path.abspath(resolved)

            if abs_resolved in norm_map:
                changed = True
                new_tracks = norm_map[abs_resolved]
                is_rel = not os.path.isabs(stripped) and not stripped.startswith('/')

                for t_path in new_tracks:
                    if t_path in seen_tracks:
                        continue
                    seen_tracks.add(t_path)
                    if is_rel:
                        entry = format_track_for_playlist(t_path, pl_path)
                    else:
                        entry = t_path
                    new_lines.append(f"{entry}\n")
            else:
                seen_tracks.add(abs_resolved)
                new_lines.append(line)

        if changed:
            tmp_path = f"{pl_path}.tmp"
            try:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                os.replace(tmp_path, pl_path)
                modified_count += 1
            except Exception:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

    return modified_count
