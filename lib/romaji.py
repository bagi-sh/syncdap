#!/usr/bin/env python3
# ==============================================================================
# Module: lib/romaji.py
# Purpose: Transliterate Japanese metadata (Kanji/Kana) to Romaji (Hepburn)
#          and sanitize filenames/folders/playlists for Rockbox DAPs & FAT32.
# ==============================================================================

import argparse
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

import mutagen
from mutagen import File
import pykakasi

# Initialize pykakasi converter
_kakasi = pykakasi.kakasi()
_print_lock = threading.Lock()

# Supported audio extensions
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

# Common symbol replacements
SYMBOL_REPLACEMENTS = {
    '℃': 'C',
    '℉': 'F',
    '＆': '&',
    '％': '%',
    '＋': '+',
    '――': '-',
    '—': '-',
    '–': '-',
    '～': '-',
    '〜': '-',
    '~': '-',
    '・': ' ',
    '…': '...',
}


def contains_japanese(text: str) -> bool:
    """Check if text contains Japanese Hiragana, Katakana, or Kanji."""
    if not text:
        return False
    return bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', text))


def sanitize_filename(name: str) -> str:
    """Sanitize name for FAT32 / exFAT filesystems."""
    if not name:
        return name

    # Normalize fullwidth ASCII characters to standard ASCII
    name = unicodedata.normalize('NFKC', name)

    for old_sym, new_sym in SYMBOL_REPLACEMENTS.items():
        name = name.replace(old_sym, new_sym)

    # Remove characters forbidden by FAT32 / exFAT: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/:*?"<>|]', '', name)

    # Normalize multiple whitespace characters
    sanitized = re.sub(r'\s+', ' ', sanitized)

    # Strip leading and trailing dots and spaces (problematic on FAT32)
    sanitized = sanitized.strip(' .')

    if not sanitized:
        return "Unknown"

    return sanitized


def to_romaji(text: str, for_filename: bool = False) -> str:
    """
    Transliterate Japanese Kana/Kanji to Romaji using Hepburn romanization.
    If text has no Japanese characters, normalize fullwidth characters without mangling text.
    If for_filename is True, apply FAT32 filename sanitization.
    """
    if not text:
        return text

    # First normalize fullwidth forms (e.g. fullwidth numbers, letters, spaces)
    normalized = unicodedata.normalize('NFKC', text)

    for old_sym, new_sym in SYMBOL_REPLACEMENTS.items():
        normalized = normalized.replace(old_sym, new_sym)

    if not contains_japanese(normalized):
        if for_filename:
            return sanitize_filename(normalized)
        return re.sub(r'\s+', ' ', normalized).strip()

    # Transliterate Japanese segments using pykakasi
    items = _kakasi.convert(normalized)
    out = []
    for item in items:
        orig = item['orig']
        hep = item['hepburn']
        if contains_japanese(orig):
            # Add space separator if adjoining alphanumeric character
            if out and re.search(r'[a-zA-Z0-9]$', out[-1]) and re.search(r'^[a-zA-Z0-9]', hep):
                out.append(' ')
            out.append(hep)
        else:
            out.append(orig)

    converted = ''.join(out)

    # Clean up double spaces and unnatural punctuation spaces
    converted = re.sub(r' +', ' ', converted)
    converted = re.sub(r'\s+([,.:;?!~）\)])', r'\1', converted)
    converted = re.sub(r'([（\(])\s+', r'\1', converted)
    converted = converted.strip()

    if for_filename:
        return sanitize_filename(converted)

    return converted


def process_audio_tags(filepath: Path, dry_run: bool) -> bool:
    """Update Japanese tags (Title, Artist, Album) to Romaji in audio metadata."""
    try:
        audio = File(filepath)
        if audio is None:
            return False

        modified = False

        # 1. MP3 with ID3 frames
        if hasattr(audio, 'tags') and audio.tags is not None and hasattr(audio.tags, 'keys'):
            for key in list(audio.tags.keys()):
                key_lower = key.lower()
                if any(k in key_lower for k in ['tit2', 'tpe1', 'talb', 'title', 'artist', 'album']):
                    frame = audio.tags[key]
                    if hasattr(frame, 'text'):
                        old_text = [str(t) for t in frame.text]
                        new_text = [to_romaji(t, for_filename=False) for t in old_text]
                        if old_text != new_text:
                            modified = True
                            with _print_lock:
                                print(f"   [ID3 TAG] {filepath.name} ({key}): {old_text} -> {new_text}")
                            if not dry_run:
                                frame.text = new_text

        # 2. FLAC, OGG, M4A, WAV (VorbisComments / MP4Tags)
        else:
            for key in list(audio.keys()):
                key_lower = key.lower()
                if any(k in key_lower for k in ['title', 'artist', 'album', 'nam', 'art', 'alb']):
                    val = audio[key]
                    if isinstance(val, list):
                        new_val = [to_romaji(str(v), for_filename=False) for v in val]
                    else:
                        new_val = to_romaji(str(val), for_filename=False)

                    if str(val) != str(new_val):
                        modified = True
                        with _print_lock:
                            print(f"   [TAG] {filepath.name} ({key}): '{val}' -> '{new_val}'")
                        if not dry_run:
                            audio[key] = new_val

        if modified and not dry_run:
            audio.save()
            return True

        return modified

    except Exception as e:
        with _print_lock:
            print(f"   [TAG ERROR] {filepath.name}: {e}")
        return False


def process_lrc_file(lrc_path: Path, dry_run: bool) -> bool:
    """Transliterate Japanese lyrics in .lrc file preserving [mm:ss.xx] timestamps."""
    if not lrc_path.exists():
        return False

    try:
        lines = lrc_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        new_lines = []
        lrc_regex = re.compile(r"^(\[\d{2}:\d{2}(?:\.\d{2,3})?\])(.*)$")
        changed = False

        for line in lines:
            match = lrc_regex.match(line)
            if match:
                timestamp, lyric = match.groups()
                converted_lyric = to_romaji(lyric, for_filename=False)
                if converted_lyric != lyric:
                    changed = True
                new_lines.append(f"{timestamp}{converted_lyric}")
            else:
                converted_line = to_romaji(line, for_filename=False)
                if converted_line != line:
                    changed = True
                new_lines.append(converted_line)

        if changed:
            with _print_lock:
                print(f"   [LRC] Transliterated lyrics: {lrc_path.name}")
            if not dry_run:
                lrc_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return True

        return False

    except Exception as e:
        with _print_lock:
            print(f"   [LRC ERROR] {lrc_path.name}: {e}")
        return False


def resolve_playlist_track(line: str, playlist_path: Path, root_dir: Path) -> Path | None:
    """Resolve track file path referenced by a playlist entry."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    clean_line = line.lstrip("/\\")

    # Relative to root directory (e.g. /Music/... or Music/...)
    p1 = (root_dir / clean_line).resolve()
    if p1.exists():
        return p1

    # Relative to playlist directory
    p2 = (playlist_path.parent / line).resolve()
    if p2.exists():
        return p2

    # Check ../Music/ prefix relative to playlist dir
    if line.startswith('../Music/'):
        p3 = (playlist_path.parent / line).resolve()
        return p3

    return p1


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


def rename_file_or_dir(old_path: Path, new_name: str, dry_run: bool, path_map: dict) -> Path:
    """Safely rename a file or directory and update path mapping."""
    if not new_name or old_path.name == new_name:
        return old_path

    new_path = old_path.parent / new_name

    # Prevent renaming into self or parent
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


def process_playlist_file(playlist_path: Path, root_dir: Path, path_map: dict, dry_run: bool):
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
                # Transliterate #EXTINF title if it contains Japanese
                if line_str.startswith("#EXTINF:") and contains_japanese(line_str):
                    parts = line_str.split(",", 1)
                    if len(parts) == 2:
                        header, title = parts
                        new_title = to_romaji(title, for_filename=False)
                        new_lines.append(f"{header},{new_title}")
                        modified = True
                        continue
                new_lines.append(line)
                continue

            # Update path entry using path_map
            updated_line = line_str
            for old_p, new_p in path_map.items():
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

        # Rename playlist file itself if name contains Japanese
        if contains_japanese(actual_playlist_path.stem):
            new_pl_stem = to_romaji(actual_playlist_path.stem, for_filename=True)
            new_pl_name = f"{new_pl_stem}{actual_playlist_path.suffix}"
            if actual_playlist_path.name != new_pl_name:
                rename_file_or_dir(actual_playlist_path, new_pl_name, dry_run, path_map)

    except Exception as e:
        print(f"   [PLAYLIST ERROR] {actual_playlist_path.name}: {e}")


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
    audio_files: list[Path] = []
    playlists_to_update: list[Path] = []

    # 1. Target resolution
    if playlist_arg:
        pl_path = Path(playlist_arg)
        if not pl_path.is_absolute():
            # Check in Playlists directory or root
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
            print(f"❌ Error: Playlist not found: {playlist_arg}")
            return 1

        print(f"-> Mapping tracks from playlist: {pl_path.name}")
        audio_files = collect_files_from_playlist(pl_path, root_dir)
        playlists_to_update.append(pl_path)

    elif all_library:
        print(f"-> Scanning entire library at: {root_dir}")
        # Detect music root (either root_dir/Music or root_dir directly)
        music_scan_dir = root_dir / "Music" if (root_dir / "Music").is_dir() else root_dir
        playlists_scan_dir = root_dir / "Playlists" if (root_dir / "Playlists").is_dir() else root_dir

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
        print("ℹ️ No audio files found to process.")
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
    # 2a. Rename files (.ext and .lrc)
    for audio_path in audio_files:
        if not audio_path.exists() and not dry_run:
            continue

        stem = audio_path.stem
        ext = audio_path.suffix

        if contains_japanese(stem):
            new_stem = to_romaji(stem, for_filename=True)
            new_filename = f"{new_stem}{ext}"
            rename_file_or_dir(audio_path, new_filename, dry_run, path_map)

            lrc_path = audio_path.with_suffix(".lrc")
            if lrc_path.exists():
                rename_file_or_dir(lrc_path, f"{new_stem}.lrc", dry_run, path_map)

    # 2b. Rename directories bottom-up (Albums before Artists)
    parent_dirs = set()
    for f in audio_files:
        p = f.parent
        while p != root_dir and p != p.parent:
            if p.name in ('Music', 'Playlists', '.'):
                break
            parent_dirs.add(p)
            p = p.parent

    # Sort directories by depth (deepest first)
    sorted_dirs = sorted(list(parent_dirs), key=lambda d: len(d.parts), reverse=True)

    for d in sorted_dirs:
        # Check current path dynamically if parent was renamed
        current_d = Path(path_map.get(str(d), d))
        if not current_d.exists() and not dry_run:
            continue

        if contains_japanese(current_d.name):
            new_dir_name = to_romaji(current_d.name, for_filename=True)
            rename_file_or_dir(current_d, new_dir_name, dry_run, path_map)

    print(f"\n[Step 3/3] Updating playlist paths and filenames ({len(playlists_to_update)} playlist(s))...")
    for pl_path in playlists_to_update:
        process_playlist_file(pl_path, root_dir, path_map, dry_run)

    print("\n✅ Romaji transliteration completed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Transliterate Japanese music metadata (Kanji/Kana) to Romaji for Rockbox & FAT32 players."
    )
    parser.add_argument("-r", "--root-dir", type=str, default=".", help="Root directory of music library or player (e.g. /run/media/bagi/F695-0800)")
    parser.add_argument("-p", "-P", "--playlist", type=str, help="Specific playlist file or name to process")
    parser.add_argument("-a", "--all", action="store_true", help="Process entire music library and playlists")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Simulate actions without modifying files")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Number of worker threads (default: 4)")

    args = parser.parse_args()

    sys.exit(
        run_romaji_transliteration(
            root_dir_str=args.root_dir,
            playlist_arg=args.playlist,
            all_library=args.all,
            dry_run=args.dry_run,
            threads=args.threads
        )
    )


if __name__ == "__main__":
    main()
