"""Playlist relinking and path updating for patched audio formats."""

import os
from share import resolve_track_file, update_all_playlists


def update_playlists(old_rel_path, new_rel_path):
    """Replace references from old_rel_path to new_rel_path in all .m3u8 and .m3u files."""
    update_all_playlists({old_rel_path: new_rel_path})


def handle_playlist_patch(pl_path, target_format, keep_old, dry_run, temp_dir, js_args, threads, assume_yes):
    """Scan and patch tracks referenced by a specific playlist file."""
    print(f"\n[PL] Playlist mode: Inspecting entries in '{os.path.basename(pl_path)}'...")
    pl_dir = os.path.dirname(os.path.abspath(pl_path))

    target_ext = f".{target_format.lower()}"
    files_to_upgrade = []

    lines_to_remove = set()
    album_clean_decisions = {}
    artist_clean_decisions = {}
    all_keep = assume_yes

    with open(pl_path, 'r', encoding='utf-8', errors='ignore') as f:
        playlist_lines = f.readlines()

    for line in playlist_lines:
        s = line.strip()
        if not s or s.startswith('#'):
            continue

        resolved = resolve_track_file(s, pl_dir)
        if os.path.isfile(resolved):
            ext = os.path.splitext(resolved)[1].lower()
            if ext != target_ext:
                files_to_upgrade.append(os.path.relpath(resolved, '.'))
            else:
                print(f"   [SKIP] Already in {target_format.upper()}: {os.path.basename(resolved)}")
        else:
            print(f"\n   [WARN] Audio file for '{s}' does not exist on disk.")
            track_album = os.path.dirname(os.path.abspath(resolved))
            track_artist = os.path.dirname(track_album)

            remove_entry = False
            if all_keep:
                remove_entry = False
            elif track_artist in artist_clean_decisions:
                remove_entry = artist_clean_decisions[track_artist]
            elif track_album in album_clean_decisions:
                remove_entry = album_clean_decisions[track_album]
            else:
                print(f"      Expected folder: {track_album}")
                print("      Options: [y] Remove from playlist | [n] Keep in playlist | [a] Entire album | [r] Entire artist | [k] Keep all remaining")
                ans = input("      Remove this entry from the playlist? [y/N]: ").strip().lower()

                if ans in ('y', 'yes', 's', 'sim'):
                    remove_entry = True
                elif ans in ('a', 'album'):
                    album_clean_decisions[track_album] = True
                    remove_entry = True
                elif ans in ('r', 'artist', 'artista'):
                    artist_clean_decisions[track_artist] = True
                    remove_entry = True
                elif ans in ('k', 'keep', 't', 'all'):
                    all_keep = True
                    remove_entry = False
                else:
                    remove_entry = False

            if remove_entry:
                lines_to_remove.add(line)

    if lines_to_remove:
        new_lines = [l for l in playlist_lines if l not in lines_to_remove]
        with open(pl_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"   [CLEAN] {len(lines_to_remove)} missing entry(ies) removed from '{os.path.basename(pl_path)}'.")

    return sorted(list(set(files_to_upgrade)))
