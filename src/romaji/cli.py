"""CLI argument parser for Japanese Romaji transliteration."""

import argparse
import sys
from pathlib import Path

lib_dir = Path(__file__).resolve().parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from romaji.engine import run_romaji_transliteration


def main():
    parser = argparse.ArgumentParser(
        description="Transliterate Japanese music metadata (Kanji/Kana) to Romaji for Rockbox & FAT32 players."
    )
    parser.add_argument("-r", "--root-dir", type=str, default=".", help="Root directory of music library or player (default: .)")
    parser.add_argument("-p", "-P", "--playlist", type=str, help="Specific playlist file or name to process")
    parser.add_argument("-a", "--all", action="store_true", help="Process entire music library and playlists")
    parser.add_argument("-n", "-d", "--dry-run", dest="dry_run", action="store_true", help="Simulate actions without modifying files")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Number of worker threads (default: 4)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed execution diagnostics")

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
