# ==============================================================================
# Module: lib/romaji/lyrics.py
# Purpose: Transliteration of .lrc synced and unsynced lyric files
# ==============================================================================

import re
import threading
from pathlib import Path

from .translit import to_romaji, contains_japanese

_print_lock = threading.Lock()


def process_lrc_file(lrc_path: Path, dry_run: bool) -> bool:
    """Transliterate Japanese lyrics in .lrc file preserving [mm:ss.xx] timestamps."""
    if not lrc_path.exists():
        return False

    try:
        content = lrc_path.read_text(encoding="utf-8", errors="ignore")
        if not contains_japanese(content):
            return False

        lines = content.splitlines()
        new_lines = []
        lrc_regex = re.compile(r"^(\[\d{2}:\d{2}(?:\.\d{2,3})?\])(.*)$")
        changed = False

        for line in lines:
            if not contains_japanese(line):
                new_lines.append(line)
                continue

            match = lrc_regex.match(line)
            if match:
                timestamp, lyric = match.groups()
                converted_lyric = to_romaji(lyric, for_filename=False, for_folder=False)
                if converted_lyric != lyric:
                    changed = True
                new_lines.append(f"{timestamp}{converted_lyric}")
            else:
                converted_line = to_romaji(line, for_filename=False, for_folder=False)
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
