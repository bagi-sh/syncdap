#!/usr/bin/env python3
# ==============================================================================
# Module: lib/playlist_ops.py
# Purpose: Playlist inspection, creation, editing, merging, track resolution,
#          cross-playlist sharing check, and safe interactive deletion.
#          All terminal output and interactive prompts are strictly in English.
# ==============================================================================

import sys
import os
import shutil
import tempfile
import subprocess

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')


def get_default_playlist_dir():
    """Determine the standard playlist directory (preferring ../Playlists, then Playlists)."""
    if os.path.isdir('../Playlists'):
        return os.path.abspath('../Playlists')
    if os.path.isdir('Playlists'):
        return os.path.abspath('Playlists')
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl):
        return home_pl
    # If none exist, create and use ../Playlists if in music dir
    try:
        os.makedirs('../Playlists', exist_ok=True)
        return os.path.abspath('../Playlists')
    except Exception:
        os.makedirs('Playlists', exist_ok=True)
        return os.path.abspath('Playlists')


def find_playlist_file(query):
    """Find a playlist file matching query in standard locations."""
    if not query:
        return None

    query_clean = query.strip()
    # 1. Direct file check
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
        # Direct join with extension variations
        for ext in ['', '.m3u8', '.m3u']:
            candidate = os.path.join(d, query_clean + ext)
            if os.path.isfile(candidate):
                return candidate
        # Case-insensitive or stripped filename match
        for f in os.listdir(d):
            if f.lower().endswith(('.m3u8', '.m3u')):
                base = os.path.splitext(f)[0]
                if f.lower() == query_clean.lower() or base.strip().lower() == query_clean.lower():
                    return os.path.join(d, f)
        # Substring match if unique
        matches = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(('.m3u8', '.m3u')) and query_clean.lower() in f.lower()]
        if len(matches) == 1:
            return matches[0]

    return None


def get_all_playlist_files():
    """Retrieve all playlist files across standard candidate directories."""
    candidate_dirs = []
    if os.path.isdir('../Playlists'):
        candidate_dirs.append(os.path.abspath('../Playlists'))
    if os.path.isdir('Playlists'):
        candidate_dirs.append(os.path.abspath('Playlists'))
    home_pl = os.path.expanduser('~/Playlists')
    if os.path.isdir(home_pl) and home_pl not in candidate_dirs:
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


def resolve_track_file(raw_entry, pl_dir):
    """
    Resolve raw playlist line to absolute track file on disk.
    Tries exact path, and if missing, checks alternative audio extensions.
    """
    clean_entry = raw_entry.strip()
    if clean_entry.startswith('/sdcard/'):
        clean_entry = clean_entry[8:]
    elif clean_entry.startswith('sdcard/'):
        clean_entry = clean_entry[7:]

    # Check relative to pl_dir
    exact_path = os.path.normpath(os.path.join(pl_dir, clean_entry))
    if os.path.isfile(exact_path):
        return exact_path

    # Check relative to parent of pl_dir (e.g. DAP root)
    dap_root = os.path.dirname(pl_dir)
    dap_path = os.path.normpath(os.path.join(dap_root, clean_entry))
    if os.path.isfile(dap_path):
        return dap_path

    # Try searching across known extensions
    stem, _ = os.path.splitext(exact_path)
    for ext in AUDIO_EXTENSIONS:
        candidate = stem + ext
        if os.path.isfile(candidate):
            return candidate

    return exact_path


def format_track_for_playlist(track_path, pl_path):
    """Format an audio file path as relative to the playlist directory."""
    pl_dir = os.path.dirname(os.path.abspath(pl_path))
    track_abs = os.path.abspath(track_path)
    return os.path.relpath(track_abs, pl_dir)


def analyze_playlist(pl_path):
    """
    Analyze all tracks in a playlist, cross-referencing other playlists
    to identify shared tracks and calculating disk usage.
    """
    pl_path = os.path.abspath(pl_path)
    pl_dir = os.path.dirname(pl_path)

    raw_lines = []
    tracks = []
    with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            raw_lines.append(line)
            s = line.strip()
            if s and not s.startswith('#'):
                resolved = resolve_track_file(s, pl_dir)
                tracks.append({
                    'raw': s,
                    'path': resolved,
                    'exists': os.path.isfile(resolved),
                    'size': os.path.getsize(resolved) if os.path.isfile(resolved) else 0,
                    'lrc': (os.path.splitext(resolved)[0] + '.lrc') if os.path.isfile(os.path.splitext(resolved)[0] + '.lrc') else None,
                    'shared_with': []
                })

    # Cross-reference with all other playlists
    all_playlists = get_all_playlist_files()
    for other_pl in all_playlists:
        if os.path.abspath(other_pl) == pl_path:
            continue
        other_dir = os.path.dirname(other_pl)
        other_name = os.path.basename(other_pl)
        try:
            with open(other_pl, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith('#'):
                        other_resolved = resolve_track_file(s, other_dir)
                        for t in tracks:
                            if t['exists'] and os.path.abspath(t['path']) == os.path.abspath(other_resolved):
                                if other_name not in t['shared_with']:
                                    t['shared_with'].append(other_name)
        except Exception:
            pass

    return raw_lines, tracks


def delete_playlist_flow(pl_query, assume_yes=False):
    """
    Interactive or automated playlist and tracks deletion.
    Supports directory-based bulk decisions ([a] Album, [r] Artist).
    """
    pl_path = find_playlist_file(pl_query)
    if not pl_path:
        print(f"❌ Error: Playlist '{pl_query}' not found.")
        return 1

    print(f"\n📋 Analyzing playlist: {pl_path}...")
    raw_lines, tracks = analyze_playlist(pl_path)

    existing_tracks = [t for t in tracks if t['exists']]
    shared_tracks = [t for t in existing_tracks if t['shared_with']]
    total_bytes = sum(t['size'] for t in existing_tracks)
    for t in existing_tracks:
        if t['lrc'] and os.path.isfile(t['lrc']):
            total_bytes += os.path.getsize(t['lrc'])

    mb_size = total_bytes / (1024 * 1024)
    print(f"   🎵 Total entries: {len(tracks)} ({len(existing_tracks)} found on disk)")
    print(f"   💾 Disk space to free: ~{mb_size:.2f} MB")
    if shared_tracks:
        print(f"   ⚠️ Shared tracks with other playlists: {len(shared_tracks)}")
        for st in shared_tracks[:3]:
            print(f"      - {os.path.basename(st['path'])} (shared with: {', '.join(st['shared_with'])})")
        if len(shared_tracks) > 3:
            print(f"      ... and {len(shared_tracks) - 3} more.")

    # High-level confirmation
    if not assume_yes:
        print("\n" + "=" * 65)
        resp = input(f"Are you sure you want to delete playlist '{os.path.basename(pl_path)}' and its audio files? [y/N]: ").strip().lower()
        if resp not in ('y', 'yes'):
            print("🛑 Operation canceled by user.")
            return 0

    # Decision maps for bulk operations by directory
    album_decisions = {}   # parent directory -> bool
    artist_decisions = {}  # grandparent directory -> bool
    all_yes = assume_yes

    deleted_count = 0
    kept_count = 0

    for idx, t in enumerate(existing_tracks):
        track_path = t['path']
        album_dir = os.path.dirname(os.path.abspath(track_path))
        artist_dir = os.path.dirname(album_dir)
        fname = os.path.basename(track_path)

        should_delete = False

        if all_yes:
            should_delete = True
        elif artist_dir in artist_decisions:
            should_delete = artist_decisions[artist_dir]
        elif album_dir in album_decisions:
            should_delete = album_decisions[album_dir]
        else:
            shared_note = f" ⚠️ [Shared with: {', '.join(t['shared_with'])}]" if t['shared_with'] else ""
            print(f"\n[{idx + 1}/{len(existing_tracks)}] 🗑️ Track: {fname}{shared_note}")
            print(f"   Folder: {album_dir}")
            print("   Options: [y] Yes | [n] No | [a] Entire album | [r] Entire artist | [t] All remaining | [c] Cancel")
            ans = input("   Decision: ").strip().lower()

            if ans in ('c', 'cancel'):
                print("🛑 Operation aborted by user.")
                break
            elif ans in ('t', 'all'):
                all_yes = True
                should_delete = True
            elif ans in ('a', 'album'):
                album_decisions[album_dir] = True
                should_delete = True
            elif ans in ('r', 'artist'):
                artist_decisions[artist_dir] = True
                should_delete = True
            elif ans in ('y', 'yes'):
                should_delete = True
            else:
                should_delete = False

        if should_delete:
            try:
                os.remove(track_path)
                deleted_count += 1
                if t['lrc'] and os.path.isfile(t['lrc']):
                    os.remove(t['lrc'])
            except Exception as e:
                print(f"   ❌ Error deleting {track_path}: {e}")
        else:
            kept_count += 1

    # Delete playlist file itself
    try:
        os.remove(pl_path)
        print(f"\n🗑️ Playlist file '{os.path.basename(pl_path)}' removed.")
    except Exception as e:
        print(f"\n⚠️ Could not remove playlist file {pl_path}: {e}")

    # Clean empty directories
    cleaned_dirs = 0
    for root, dirs, files in os.walk('.', topdown=False):
        if root != '.' and not os.listdir(root):
            try:
                os.rmdir(root)
                cleaned_dirs += 1
            except Exception:
                pass

    print(f"\n✅ Completed: {deleted_count} track(s) deleted, {kept_count} track(s) kept.")
    if cleaned_dirs > 0:
        print(f"🧹 Cleaned up {cleaned_dirs} empty folder(s).")

    return 0


def merge_playlists_flow(pl1_query, pl2_query, out_name=None, delete_sources=False, assume_yes=False):
    """
    Merge two playlists into one, deduplicating tracks and optionally
    removing the source playlist files.
    """
    pl1_path = find_playlist_file(pl1_query)
    pl2_path = find_playlist_file(pl2_query)

    if not pl1_path:
        print(f"❌ Error: Source playlist 1 '{pl1_query}' not found.")
        return 1
    if not pl2_path:
        print(f"❌ Error: Source playlist 2 '{pl2_query}' not found.")
        return 1

    if os.path.abspath(pl1_path) == os.path.abspath(pl2_path):
        print("❌ Error: Cannot merge a playlist with itself. Please specify two distinct playlists.")
        return 1

    pl_dir = os.path.dirname(os.path.abspath(pl1_path))

    # Read items from PL1
    print(f"\n🔗 Merging playlists:")
    print(f"   [1] {os.path.basename(pl1_path)}")
    print(f"   [2] {os.path.basename(pl2_path)}")

    def read_playlist_entries(p):
        entries = []
        cur_comments = []
        p_dir = os.path.dirname(os.path.abspath(p))
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#EXTM3U'):
                    continue
                if s.startswith('#'):
                    cur_comments.append(s)
                else:
                    resolved = resolve_track_file(s, p_dir)
                    entries.append({
                        'raw': s,
                        'resolved': resolved,
                        'comments': list(cur_comments)
                    })
                    cur_comments.clear()
        return entries

    entries_1 = read_playlist_entries(pl1_path)
    entries_2 = read_playlist_entries(pl2_path)

    # Combine and deduplicate
    seen_paths = set()
    merged_entries = []

    for item in entries_1:
        key = os.path.abspath(item['resolved'])
        if key not in seen_paths:
            seen_paths.add(key)
            merged_entries.append(item)

    for item in entries_2:
        key = os.path.abspath(item['resolved'])
        if key not in seen_paths:
            seen_paths.add(key)
            merged_entries.append(item)

    # Determine destination playlist file
    if not out_name:
        default_name = f"{os.path.splitext(os.path.basename(pl1_path))[0]}_{os.path.splitext(os.path.basename(pl2_path))[0]}.m3u8"
        if not assume_yes:
            prompt_name = input(f"Enter merged playlist name (default: '{default_name}'): ").strip()
            out_name = prompt_name if prompt_name else default_name
        else:
            out_name = default_name

    if not out_name.lower().endswith(('.m3u8', '.m3u')):
        out_name += '.m3u8'

    dest_pl_path = os.path.join(pl_dir, out_name)

    # Write merged playlist
    out_lines = ['#EXTM3U\n']
    for item in merged_entries:
        for c in item['comments']:
            out_lines.append(f"{c}\n")
        # Relative format to dest_pl_path
        rel_track = format_track_for_playlist(item['resolved'], dest_pl_path)
        out_lines.append(f"{rel_track}\n")

    with open(dest_pl_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    print(f"\n✅ Merged playlist saved successfully!")
    print(f"   📍 File: {dest_pl_path}")
    print(f"   🎶 Total tracks: {len(merged_entries)} ({len(entries_1)} from PL1, {len(entries_2)} from PL2)")

    # Prompt or handle source playlist deletion
    should_del_sources = delete_sources
    if not delete_sources and not assume_yes:
        ans = input(f"\nDo you want to delete the two source playlist files ('{os.path.basename(pl1_path)}' & '{os.path.basename(pl2_path)}')? [y/N]: ").strip().lower()
        if ans in ('y', 'yes'):
            should_del_sources = True

    if should_del_sources:
        try:
            if os.path.isfile(pl1_path) and os.path.abspath(pl1_path) != os.path.abspath(dest_pl_path):
                os.remove(pl1_path)
                print(f"   🗑️ Removed source playlist: {os.path.basename(pl1_path)}")
            if os.path.isfile(pl2_path) and os.path.abspath(pl2_path) != os.path.abspath(dest_pl_path):
                os.remove(pl2_path)
                print(f"   🗑️ Removed source playlist: {os.path.basename(pl2_path)}")
        except Exception as e:
            print(f"   ⚠️ Could not delete source playlist files: {e}")
    else:
        print("   ℹ️ Source playlists kept intact.")

    return 0


def select_with_fzf(items, prompt="Select > ", header="", multi=False, preview_cmd=None):
    """Interactive selector helper using fzf or simple fallback."""
    if not items:
        return [] if multi else None

    if shutil.which('fzf'):
        cmd = ['fzf', '--prompt', prompt]
        if header:
            cmd.extend(['--header', header])
        if multi:
            cmd.extend(['--multi', '--bind', 'alt-a:select-all,alt-d:deselect-all'])
        if preview_cmd:
            cmd.extend(['--preview', preview_cmd, '--preview-window', 'down:3:wrap'])

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate(input='\n'.join(items))
        if proc.returncode == 0 and out.strip():
            selected = [l.strip() for l in out.strip().splitlines() if l.strip()]
            return selected if multi else selected[0]
        return [] if multi else None

    # Fallback when fzf is not installed
    print(f"\n{header or prompt}")
    for i, it in enumerate(items, 1):
        print(f"  [{i}] {it}")
    choice = input("Enter number (or press Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        chosen = items[int(choice) - 1]
        return [chosen] if multi else chosen
    return [] if multi else None


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
        # CREATE NEW PLAYLIST
        pl_name = input("Enter new playlist name (e.g. My Favorites): ").strip()
        if not pl_name:
            print("❌ Invalid playlist name.")
            return 1
        if not pl_name.lower().endswith(('.m3u8', '.m3u')):
            pl_name += '.m3u8'

        dest_path = os.path.join(pl_dir, pl_name)

        # Scan library audio files
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

        # Review and save
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
        # EDIT PLAYLIST
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

        # Scan library audio files
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

        # Merge new additions with existing preserving order and deduplicating
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
        # MERGE PLAYLISTS
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
        # DELETE PLAYLIST
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


if __name__ == '__main__':
    if len(sys.argv) < 2:
        interactive_playlist_manager()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == '--delete':
        target = sys.argv[2] if len(sys.argv) > 2 else ""
        yes_flag = '--yes' in sys.argv or '-y' in sys.argv
        sys.exit(delete_playlist_flow(target, yes_flag))
    elif cmd == '--merge':
        pl1 = sys.argv[2] if len(sys.argv) > 2 else ""
        pl2 = sys.argv[3] if len(sys.argv) > 3 else ""
        out_name = None
        del_src = False
        yes_flag = False
        for arg in sys.argv[4:]:
            if arg in ('--delete-sources', '--delete'):
                del_src = True
            elif arg in ('--yes', '-y'):
                yes_flag = True
            elif not arg.startswith('-') and not out_name:
                out_name = arg
        sys.exit(merge_playlists_flow(pl1, pl2, out_name, del_src, yes_flag))
    elif cmd in ('--menu', '-P', '--playlist'):
        sys.exit(interactive_playlist_manager())
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
