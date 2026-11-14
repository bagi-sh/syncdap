# ==============================================================================
# Module: lib/playlists/actions.py
# Purpose: Playlist deletion and merging workflows
# ==============================================================================

import os
from .core import (
    find_playlist_file,
    get_all_playlist_files,
    resolve_track_file,
    format_track_for_playlist,
    analyze_playlist,
)


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

    if not assume_yes:
        print("\n" + "=" * 65)
        resp = input(f"Are you sure you want to delete playlist '{os.path.basename(pl_path)}' and its audio files? [y/N]: ").strip().lower()
        if resp not in ('y', 'yes'):
            print("🛑 Operation canceled by user.")
            return 0

    album_decisions = {}
    artist_decisions = {}
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

    try:
        os.remove(pl_path)
        print(f"\n🗑️ Playlist file '{os.path.basename(pl_path)}' removed.")
    except Exception as e:
        print(f"\n⚠️ Could not remove playlist file {pl_path}: {e}")

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
    """Merge two playlists into one, deduplicating tracks."""
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

    out_lines = ['#EXTM3U\n']
    for item in merged_entries:
        for c in item['comments']:
            out_lines.append(f"{c}\n")
        rel_track = format_track_for_playlist(item['resolved'], dest_pl_path)
        out_lines.append(f"{rel_track}\n")

    with open(dest_pl_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

    print(f"\n✅ Merged playlist saved successfully!")
    print(f"   📍 File: {dest_pl_path}")
    print(f"   🎶 Total tracks: {len(merged_entries)} ({len(entries_1)} from PL1, {len(entries_2)} from PL2)")

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
