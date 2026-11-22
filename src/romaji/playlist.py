"""Playlist relinking for Romaji renamed tracks."""

from pathlib import Path

from share import resolve_track_file
from .translit import AUDIO_EXTENSIONS, contains_japanese, to_romaji


def resolve_playlist_track(line: str, playlist_path: Path, root_dir: Path) -> Path | None:
    """Resolve track file path referenced by a playlist entry."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    res = resolve_track_file(line, playlist_dir=str(playlist_path.parent), music_roots=[str(root_dir)])
    return Path(res)


def collect_files_from_playlist(playlist_path: Path, root_dir: Path) -> list[Path]:
    """Collect all valid audio file paths from a playlist."""
    if not playlist_path.exists():
        print(f"[ERROR] Playlist not found: {playlist_path}")
        return []

    tracks = []
    lines = playlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in lines:
        track_path = resolve_playlist_track(line, playlist_path, root_dir)
        if track_path and track_path.suffix.lower() in AUDIO_EXTENSIONS:
            tracks.append(track_path)
    return tracks


def process_playlist_file(playlist_path: Path, root_dir: Path, path_map: dict, dry_run: bool, rename_fn=None):
    """Update track references in playlist file and rename playlist if needed."""
    actual_playlist_path = Path(path_map.get(str(playlist_path), playlist_path))
    if not actual_playlist_path.exists() and not dry_run:
        return

    try:
        if actual_playlist_path.exists():
            lines = actual_playlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        else:
            lines = playlist_path.read_text(encoding="utf-8", errors="ignore").splitlines()

        new_lines = []
        modified = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                new_lines.append(line)
                continue

            if line_str.startswith("#"):
                if line_str.startswith("#EXTINF:") and contains_japanese(line_str):
                    parts = line_str.split(",", 1)
                    if len(parts) == 2:
                        header, title = parts
                        new_title = to_romaji(title, for_filename=False, for_folder=False)
                        new_lines.append(f"{header},{new_title}")
                        modified = True
                        continue
                new_lines.append(line)
                continue

            updated_line = line_str
            for old_p, new_p in sorted(path_map.items(), key=lambda x: len(Path(x[0]).name), reverse=True):
                old_name = Path(old_p).name
                new_name = Path(new_p).name
                if old_name != new_name and old_name in updated_line:
                    updated_line = updated_line.replace(old_name, new_name)

            if updated_line != line_str:
                modified = True

            new_lines.append(updated_line)

        if modified:
            print(f"   [PLAYLIST] Updating paths in: {actual_playlist_path.name}")
            if not dry_run and actual_playlist_path.exists():
                actual_playlist_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        if contains_japanese(actual_playlist_path.stem):
            new_pl_stem = to_romaji(actual_playlist_path.stem, for_filename=True, for_folder=False)
            new_pl_name = f"{new_pl_stem}{actual_playlist_path.suffix}"
            if actual_playlist_path.name != new_pl_name and rename_fn:
                rename_fn(actual_playlist_path, new_pl_name, dry_run, path_map)

    except Exception as e:
        print(f"   [PLAYLIST ERROR] {actual_playlist_path.name}: {e}")
