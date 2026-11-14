#!/usr/bin/env python3
# ==============================================================================
# Module: lib/playlist_ops.py
# Purpose: Backward-compatible shim for lib/playlists module
# ==============================================================================

import os
import sys
from pathlib import Path

lib_dir = Path(__file__).resolve().parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from playlists import (
    AUDIO_EXTENSIONS,
    get_default_playlist_dir,
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
    analyze_playlist,
    select_with_fzf,
    delete_playlist_flow,
    merge_playlists_flow,
    interactive_playlist_manager,
    main,
)

if __name__ == '__main__':
    main()
