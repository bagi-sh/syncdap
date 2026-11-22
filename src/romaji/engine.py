"""Japanese Romaji batch transliteration engine."""

import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .translit import AUDIO_EXTENSIONS, contains_japanese, to_romaji
from .tags import process_audio_tags
from .lyrics import process_lrc_file
from .playlist import collect_files_from_playlist, process_playlist_file


def rename_file_or_dir(old_path: Path, new_name: str, dry_run: bool, path_map: dict) -> Path:
    """Safely rename a file or directory and update path mapping."""
    if not new_name or old_path.name == new_name:
        return old_path

    new_path = old_path.parent / new_name

    if new_path == old_path.parent:
        print(f"   [WARNING] Invalid name ignored: '{old_path.name}'")
        return old_path

    try:
        rel_label = old_path.relative_to(old_path.anchor)
    except ValueError:
        rel_label = old_path

    print(f"   [RENAME] {rel_label} -> {new_name}")
    path_map[str(old_path)] = str(new_path)

    if not dry_run:
        try:
            if old_path.exists():
                old_path.rename(new_path)
        except OSError as e:
            print(f"   [RENAME ERROR] Could not move '{old_path.name}': {e}")
            return old_path

    return new_path


def run_romaji_transliteration(
    root_dir_str: str = ".",
    playlist_arg: str | None = None,
    all_library: bool = False,
    dry_run: bool = False,
    threads: int = 4
) -> int:
    """Main execution flow for Romaji transliteration across library or playlist."""
    root_dir = Path(root_dir_str).resolve()

    if dry_run:
        print("\n=== [DRY-RUN MODE ACTIVATED] ===")
        print("No changes will be written to disk.\n")

    if not playlist_arg and not all_library:
        print("Error: Specify a mode: --all or --playlist <path/name>")
        return 1

    path_map: dict[str, str] = {}
    dir_map: dict[str, str] = {}
    audio_files: list[Path] = []
    playlists_to_update: list[Path] = []

    music_scan_dir = root_dir / "Music" if (root_dir / "Music").is_dir() else root_dir
    playlists_scan_dir = root_dir / "Playlists" if (root_dir / "Playlists").is_dir() else root_dir

    # 1. Target resolution
    if playlist_arg:
        pl_path = Path(playlist_arg)
        if not pl_path.is_absolute():
            if (root_dir / "Playlists" / pl_path).exists():
                pl_path = root_dir / "Playlists" / pl_path
            elif (root_dir / pl_path).exists():
                pl_path = root_dir / pl_path
            elif not pl_path.suffix:
                for ext in ['.m3u8', '.m3u']:
                    candidate = root_dir / "Playlists" / f"{playlist_arg}{ext}"
                    if candidate.exists():
                        pl_path = candidate
                        break

        if not pl_path.exists():
            print(f"[ERR] Error: Playlist not found: {playlist_arg}")
            return 1

        print(f"-> Mapping tracks from playlist: {pl_path.name}")
        audio_files = collect_files_from_playlist(pl_path, root_dir)
        playlists_to_update.append(pl_path)

    elif all_library:
        print(f"-> Scanning entire library at: {root_dir}")
        for root, dirs, files in os.walk(music_scan_dir):
            rel = os.path.relpath(root, root_dir)
            if rel.startswith(('Playlists', 'lib', '.git', '.rockbox', 'LOST.DIR', 'System Volume Information')):
                continue
            for f in files:
                if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(Path(root) / f)

        if playlists_scan_dir.exists():
            for root, _, files in os.walk(playlists_scan_dir):
                for f in files:
                    if f.lower().endswith(('.m3u', '.m3u8')):
                        playlists_to_update.append(Path(root) / f)

    if not audio_files:
        print("[INFO] No audio files found to process.")
        return 0

    print(f"\n[Step 1/3] Processing audio tags & .lrc lyrics ({len(audio_files)} tracks)...")
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for audio_path in audio_files:
            if audio_path.exists():
                executor.submit(process_audio_tags, audio_path, dry_run)
                lrc_path = audio_path.with_suffix(".lrc")
                if lrc_path.exists():
                    executor.submit(process_lrc_file, lrc_path, dry_run)

    print(f"\n[Step 2/3] Renaming audio files, lyrics, and directory hierarchy...")
    for audio_path in audio_files:
        if not audio_path.exists() and not dry_run:
            continue

        stem = audio_path.stem
        ext = audio_path.suffix

        if contains_japanese(stem):
            new_stem = to_romaji(stem, for_filename=True, for_folder=False)
            new_filename = f"{new_stem}{ext}"
            rename_file_or_dir(audio_path, new_filename, dry_run, path_map)

            lrc_path = audio_path.with_suffix(".lrc")
            if lrc_path.exists():
                rename_file_or_dir(lrc_path, f"{new_stem}.lrc", dry_run, path_map)

    parent_dirs = set()
    for f in audio_files:
        p = f.parent
        while p != root_dir and p != p.parent:
            if p.name in ('Music', 'Playlists', '.'):
                break
            parent_dirs.add(p)
            p = p.parent

    if all_library and music_scan_dir.exists():
        for root, dirs, _ in os.walk(music_scan_dir):
            rel = os.path.relpath(root, root_dir)
            if rel.startswith(('Playlists', 'lib', '.git', '.rockbox', 'LOST.DIR', 'System Volume Information')):
                continue
            for d in dirs:
                if contains_japanese(d):
                    p = Path(root) / d
                    while p != root_dir and p != p.parent:
                        if p.name in ('Music', 'Playlists', '.'):
                            break
                        parent_dirs.add(p)
                        p = p.parent

    def resolve_current_dir(target_dir: Path) -> Path:
        parts = list(target_dir.parts)
        cur = Path(parts[0])
        for part in parts[1:]:
            cand = cur / part
            if str(cand) in dir_map:
                cur = Path(dir_map[str(cand)])
            else:
                cur = cand
        return cur

    sorted_dirs = sorted(list(parent_dirs), key=lambda d: len(d.parts), reverse=True)

    for d in sorted_dirs:
        current_d = resolve_current_dir(d)
        if not current_d.exists() and not dry_run:
            continue

        if contains_japanese(current_d.name):
            new_dir_name = to_romaji(current_d.name, for_filename=True, for_folder=True)
            new_d = rename_file_or_dir(current_d, new_dir_name, dry_run, path_map)
            dir_map[str(d)] = str(new_d)
            dir_map[str(current_d)] = str(new_d)

    print(f"\n[Step 3/3] Updating playlist paths and filenames ({len(playlists_to_update)} playlist(s))...")
    for pl_path in playlists_to_update:
        process_playlist_file(pl_path, root_dir, path_map, dry_run, rename_fn=rename_file_or_dir)

    print("\n[OK] Romaji transliteration completed successfully!")
    return 0
