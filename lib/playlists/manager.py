# ==============================================================================
# Module: lib/playlists/manager.py
# Purpose: Interactive playlist manager menu
# ==============================================================================

import os
from .core import (
    AUDIO_EXTENSIONS,
    get_default_playlist_dir,
    get_all_playlist_files,
    find_playlist_file,
    format_track_for_playlist,
    analyze_playlist,
)
from .ui import select_with_fzf
from .actions import merge_playlists_flow, delete_playlist_flow


def interactive_playlist_manager():
    """Interactive CLI menu for managing playlists (create, edit, merge, delete)."""
    print("🎵 Interactive M3U8 Playlist Manager")
    print("------------------------------------------")

    actions = [
        "1. Create a new playlist",
        "2. Edit an existing playlist",
        "3. Merge two playlists into one",
        "4. Delete a playlist and its audio files"
    ]

    action = select_with_fzf(actions, prompt="Action > ", header="[ Choose an action ]")
    if not action:
        print("⚠️ No action selected. Operation canceled.")
        return 0

    pl_dir = get_default_playlist_dir()

    if action.startswith("1"):
        pl_name = input("Enter new playlist name (e.g. My Favorites): ").strip()
        if not pl_name:
            print("❌ Invalid playlist name.")
            return 1
        if not pl_name.lower().endswith(('.m3u8', '.m3u')):
            pl_name += '.m3u8'

        dest_path = os.path.join(pl_dir, pl_name)

        print("\n🔍 Scanning library for audio files...")
        all_tracks = []
        for root, dirs, files in os.walk('.'):
            if root.startswith('./Playlists') or root == './Playlists':
                continue
            for f in files:
                if f.lower().endswith(AUDIO_EXTENSIONS):
                    all_tracks.append(os.path.normpath(os.path.join(root, f)))
        all_tracks.sort()

        if not all_tracks:
            print("❌ No audio files found in current directory.")
            return 1

        selected = select_with_fzf(
            all_tracks,
            prompt="Tracks > ",
            header="[ TAB: Select/Deselect | Alt+A: Select All | Enter: Confirm ]",
            multi=True
        )

        if not selected:
            print("⚠️ No tracks selected. Playlist creation canceled.")
            return 0

        out_lines = ['#EXTM3U\n']
        for t in selected:
            out_lines.append(f"{format_track_for_playlist(t, dest_path)}\n")

        with open(dest_path, 'w', encoding='utf-8') as fp:
            fp.writelines(out_lines)

        print(f"\n✅ Playlist created successfully!")
        print(f"   📍 File: {dest_path}")
        print(f"   🎶 Total tracks: {len(selected)}")
        return 0

    elif action.startswith("2"):
        all_pls = get_all_playlist_files()
        if not all_pls:
            print(f"❌ No playlist files found in '{pl_dir}'.")
            return 1

        pl_names = [os.path.basename(p) for p in all_pls]
        selected_pl_name = select_with_fzf(pl_names, prompt="Playlist > ", header="[ Select playlist to edit ]")
        if not selected_pl_name:
            print("⚠️ No playlist selected. Operation canceled.")
            return 0

        selected_pl = find_playlist_file(selected_pl_name)
        raw_lines, tracks = analyze_playlist(selected_pl)

        existing_track_rel = []
        for t in tracks:
            existing_track_rel.append(os.path.relpath(t['path'], '.'))

        all_tracks = []
        for root, dirs, files in os.walk('.'):
            if root.startswith('./Playlists') or root == './Playlists':
                continue
            for f in files:
                if f.lower().endswith(AUDIO_EXTENSIONS):
                    all_tracks.append(os.path.normpath(os.path.join(root, f)))
        all_tracks.sort()

        print(f"\n📖 Loaded playlist '{selected_pl_name}' with {len(existing_track_rel)} track(s).")
        added_tracks = select_with_fzf(
            all_tracks,
            prompt="Add/Select Tracks > ",
            header="[ Select additional tracks to add ]",
            multi=True
        )

        combined = list(existing_track_rel)
        for t in added_tracks:
            if t not in combined:
                combined.append(t)

        out_lines = ['#EXTM3U\n']
        for t in combined:
            out_lines.append(f"{format_track_for_playlist(t, selected_pl)}\n")

        with open(selected_pl, 'w', encoding='utf-8') as fp:
            fp.writelines(out_lines)

        print(f"\n✅ Playlist updated successfully!")
        print(f"   📍 File: {selected_pl}")
        print(f"   🎶 Total tracks: {len(combined)}")
        return 0

    elif action.startswith("3"):
        all_pls = get_all_playlist_files()
        if len(all_pls) < 2:
            print(f"❌ Need at least 2 playlists to merge. Found {len(all_pls)}.")
            return 1

        pl_names = [os.path.basename(p) for p in all_pls]
        pl1 = select_with_fzf(pl_names, prompt="Source Playlist 1 > ", header="[ Select first playlist to merge ]")
        if not pl1:
            return 0

        remaining_pls = [p for p in pl_names if p != pl1]
        pl2 = select_with_fzf(remaining_pls, prompt="Source Playlist 2 > ", header="[ Select second playlist to merge ]")
        if not pl2:
            return 0

        return merge_playlists_flow(pl1, pl2)

    elif action.startswith("4"):
        all_pls = get_all_playlist_files()
        if not all_pls:
            print("❌ No playlists found.")
            return 1
        pl_names = [os.path.basename(p) for p in all_pls]
        chosen = select_with_fzf(pl_names, prompt="Delete Playlist > ", header="[ Select playlist to delete ]")
        if not chosen:
            return 0
        return delete_playlist_flow(chosen, assume_yes=False)

    return 0
