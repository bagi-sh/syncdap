# ==============================================================================
# Module: src/share/playlists.py
# Purpose: Shared playlist discovery, track resolution, parsing, and atomic patching
#          (supporting both 1-to-1 and 1-to-N track replacements).
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


def clean_playlist_entry(entry: str) -> str:
    """Strip standard DAP prefixes (/sdcard/Music/, ../Music/, Music/, etc.)."""
    s = entry.strip()
    for pfx in ['/sdcard/Music/', 'sdcard/Music/', '/sdcard/', 'sdcard/', '../Music/', 'Music/', './']:
        if s.startswith(pfx):
            s = s[len(pfx):]
            break
    return s.lstrip('/\\')


def resolve_track_file(raw_entry: str, pl_dir: str, search_roots: list[str] | None = None) -> str:
    """
    Resolve raw playlist line to absolute track file on disk.
    Tries relative paths, DAP root prefixes, search_roots, and alternative audio extensions.
    """
    clean_entry = clean_playlist_entry(raw_entry)

    # 1. Direct path relative to playlist directory
    exact_path = os.path.normpath(os.path.join(pl_dir, clean_entry))
    if os.path.isfile(exact_path):
        return os.path.abspath(exact_path)

    # 2. Relative to parent of playlist directory (standard DAP layout)
    dap_root = os.path.dirname(os.path.abspath(pl_dir))
    dap_path = os.path.normpath(os.path.join(dap_root, clean_entry))
    if os.path.isfile(dap_path):
        return os.path.abspath(dap_path)

    dap_music = os.path.normpath(os.path.join(dap_root, 'Music', clean_entry))
    if os.path.isfile(dap_music):
        return os.path.abspath(dap_music)

    # 3. Search roots if provided
    if search_roots:
        for r in search_roots:
            if not r:
                continue
            cand1 = os.path.normpath(os.path.join(r, clean_entry))
            if os.path.isfile(cand1):
                return os.path.abspath(cand1)
            cand2 = os.path.normpath(os.path.join(r, 'Music', clean_entry))
            if os.path.isfile(cand2):
                return os.path.abspath(cand2)

    # 4. Alternative audio extensions
    stem, _ = os.path.splitext(exact_path)
    for ext in AUDIO_EXTENSIONS:
        candidate = stem + ext
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    stem_dap, _ = os.path.splitext(dap_path)
    for ext in AUDIO_EXTENSIONS:
        candidate = stem_dap + ext
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return os.path.abspath(exact_path)


def format_track_for_playlist(track_path: str, pl_path: str) -> str:
    """Format an audio file path as relative to the playlist directory."""
    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    track_abs = os.path.abspath(track_path)
    return os.path.relpath(track_abs, pl_dir)


def parse_playlist_file(pl_path: str, search_roots: list[str] | None = None) -> list[dict]:
    """
    Parse a playlist file preserving comments (#EXTINF) and resolving track paths.
    Returns list of dicts: {'raw': str, 'resolved': str, 'comments': list[str], 'exists': bool}.
    """
    entries = []
    if not pl_path or not os.path.isfile(pl_path):
        return entries

    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    cur_comments = []

    try:
        with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#EXTM3U'):
                    continue
                if s.startswith('#'):
                    cur_comments.append(s)
                else:
                    resolved = resolve_track_file(s, pl_dir, search_roots)
                    entries.append({
                        'raw': s,
                        'resolved': resolved,
                        'comments': list(cur_comments),
                        'exists': os.path.isfile(resolved),
                    })
                    cur_comments.clear()
    except Exception:
        pass

    return entries


def patch_playlist_file(pl_path: str, replacements: dict[str, str | list[str]]) -> bool:
    """
    Atomically patch a playlist replacing old track paths with new path(s).
    Supports 1-to-1 replacements (str) and 1-to-N replacements (list[str]).
    Preserves #EXTINF comments and deduplicates tracks inside the playlist.
    Returns True if the playlist was modified, False otherwise.
    """
    if not pl_path or not os.path.isfile(pl_path) or not replacements:
        return False

    norm_replacements: dict[str, list[str]] = {}
    for k, v in replacements.items():
        if isinstance(v, list):
            norm_replacements[os.path.abspath(k)] = [os.path.abspath(x) for x in v if x]
        elif v:
            norm_replacements[os.path.abspath(k)] = [os.path.abspath(v)]

    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    try:
        with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return False

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

        if abs_resolved in norm_replacements:
            changed = True
            new_tracks = norm_replacements[abs_resolved]
            is_rel = not os.path.isabs(stripped) and not stripped.startswith('/')

            for t_path in new_tracks:
                if t_path in seen_tracks:
                    continue
                seen_tracks.add(t_path)
                entry = format_track_for_playlist(t_path, pl_path) if is_rel else t_path
                new_lines.append(f"{entry}\n")
        else:
            if abs_resolved in seen_tracks:
                # Deduplicate repeated tracks in playlist
                if new_lines and new_lines[-1].startswith('#EXTINF'):
                    new_lines.pop()
                changed = True
                continue
            seen_tracks.add(abs_resolved)
            new_lines.append(line)

    if changed:
        tmp_path = f"{pl_path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            os.replace(tmp_path, pl_path)
            return True
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    return False


def update_all_playlists(
    search_roots: list[str] | str | None,
    replacements: dict[str, str | list[str]],
) -> int:
    """Apply atomic track replacements across all playlists found in search_roots."""
    if not replacements:
        return 0

    roots = [search_roots] if isinstance(search_roots, str) else (search_roots or [])
    all_pls = get_all_playlist_files(roots)
    modified = 0

    for pl in all_pls:
        if patch_playlist_file(pl, replacements):
            modified += 1

    return modified


# Backward-compatible alias
expand_playlist_entries = update_all_playlists
