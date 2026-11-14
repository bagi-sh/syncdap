# ==============================================================================
# Module: src/patch/cli.py
# Purpose: CLI argument parser and batch execution for patch operations
# ==============================================================================

import os
import sys
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

lib_dir = Path(__file__).resolve().parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from share import find_playlist_file, AUDIO_EXTENSIONS
from patch.playlist import handle_playlist_patch
from patch.worker import upgrade_track


def main():
    if len(sys.argv) < 3:
        print("Usage: patch.py <target_format> <temp_dir> [threads] [keep_old] [dry_run] [filter_term] [js_args] [assume_yes]")
        sys.exit(1)

    target_format = sys.argv[1].lower()
    temp_dir = sys.argv[2]
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    keep_old = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False
    dry_run = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False
    filter_term = sys.argv[6] if len(sys.argv) > 6 else ""
    ytdlp_js_raw = sys.argv[7] if len(sys.argv) > 7 else ""
    assume_yes = sys.argv[8].lower() == 'true' if len(sys.argv) > 8 else False

    js_args = ytdlp_js_raw.split() if ytdlp_js_raw else []
    target_ext = f".{target_format}"

    files_to_upgrade = []
    matched_pl = find_playlist_file(filter_term) if filter_term else None

    if matched_pl:
        files_to_upgrade = handle_playlist_patch(
            matched_pl, target_format, keep_old, dry_run, temp_dir, js_args, threads, assume_yes
        )
    else:
        for root, _, files in os.walk('.'):
            if root.startswith('./Playlists') or root == '.':
                continue
            if filter_term and filter_term.lower() not in root.lower():
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTENSIONS and ext != target_ext:
                    files_to_upgrade.append(os.path.join(root, f))

        files_to_upgrade.sort()

    total = len(files_to_upgrade)
    if total == 0:
        print(f"   ✨ No tracks requiring patch to {target_format.upper()} were found.")
        sys.exit(0)

    print(f"   Found {total} track(s) for quality patch to {target_format.upper()} using {threads} worker(s)...")
    if keep_old:
        print("   🛡️ Mode: --keep-old enabled (original files will not be deleted).")
    if dry_run:
        print("   🔍 Mode: --dry-run enabled (simulating patch without changes).")

    counters = {'upgraded': 0, 'skipped': 0, 'failed': 0}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(
                upgrade_track,
                i + 1,
                total,
                f,
                target_format,
                keep_old,
                dry_run,
                temp_dir,
                js_args,
                counters,
                lock
            )
            for i, f in enumerate(files_to_upgrade)
        ]
        for f in futures:
            f.result()

    print(f"\n   📊 Patch completed: {counters['upgraded']} patched, {counters['skipped']} skipped, {counters['failed']} failed out of {total}.")


if __name__ == '__main__':
    main()
