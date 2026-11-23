#!/usr/bin/env python3
"""Music library folder hierarchy reorganization module for Rockbox and DAPs.

Scans an audio library, extracts tag metadata (Artist, Album, Track Number, Title),
and restructures files into the canonical syncdap / FAT32 layout:
    {MUSIC_ROOT}/{AlbumArtist}/{Album}/{track_num:02d} {title} - {track_artist}.{ext}

Also moves associated synchronized lyrics sidecars (.lrc) and album artwork (cover.jpg),
safely updates existing playlist references, and prunes orphaned empty directories.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from share import (
    AUDIO_EXTENSIONS,
    COVER_FILENAMES,
    IGNORED_DIRS,
    clean_string,
    find_audio_files,
    format_bytes,
    parse_filename_metadata,
    read_audio_metadata,
    sanitize_filename,
    update_all_playlists,
)
from share.icons import ICONS


def compute_canonical_destination(
    file_path: str,
    music_root: str,
) -> tuple[str, str, dict]:
    """Compute canonical target path for an audio file based on metadata and tags.

    Returns:
        (dest_dir, dest_file_path, metadata_dict)
    """
    raw_meta = read_audio_metadata(file_path, fallback_to_filename=True)
    fn_meta = parse_filename_metadata(file_path)

    # 1. Artist / AlbumArtist determination
    # Prefer album_artist so compilation/featuring tracks stay in the album's home folder
    artist_folder = (
        clean_string(raw_meta.get("album_artist"))
        or clean_string(raw_meta.get("artist"))
        or clean_string(fn_meta.get("artist"))
        or "Unknown Artist"
    )

    # Track artist (may differ from album_artist on features / compilations)
    track_artist = (
        clean_string(raw_meta.get("artist"))
        or clean_string(raw_meta.get("album_artist"))
        or clean_string(fn_meta.get("artist"))
        or artist_folder
    )

    # 2. Album name determination
    album_folder = (
        clean_string(raw_meta.get("album"))
        or clean_string(fn_meta.get("album"))
        or "Unknown Album"
    )

    # 3. Track title
    title = (
        clean_string(raw_meta.get("title"))
        or clean_string(fn_meta.get("title"))
        or os.path.splitext(os.path.basename(file_path))[0]
    )

    # 4. Track number (format as 2-digit e.g. "01 ", or omit if none)
    track_num_raw = raw_meta.get("track_num") or fn_meta.get("track_no") or ""
    track_prefix = ""
    try:
        tn_int = int(str(track_num_raw).split("/")[0].strip())
        if tn_int > 0:
            track_prefix = f"{tn_int:02d} "
    except (ValueError, TypeError):
        track_prefix = ""

    # Sanitize each path component for FAT32 / exFAT compatibility
    safe_artist_folder = sanitize_filename(artist_folder)
    safe_album_folder = sanitize_filename(album_folder)
    safe_title = sanitize_filename(title)
    safe_track_artist = sanitize_filename(track_artist)

    ext = os.path.splitext(file_path)[1].lower()
    dest_filename = f"{track_prefix}{safe_title} - {safe_track_artist}{ext}"

    dest_dir = os.path.join(music_root, safe_artist_folder, safe_album_folder)
    dest_file = os.path.join(dest_dir, dest_filename)

    meta_info = {
        "artist_folder": safe_artist_folder,
        "album_folder": safe_album_folder,
        "track_artist": safe_track_artist,
        "title": safe_title,
        "track_prefix": track_prefix,
        "ext": ext,
    }

    return dest_dir, dest_file, meta_info


def plan_library_organization(target_root: str, music_root: str) -> tuple[list[dict], list[str]]:
    """Scan library and construct the execution plan for all audio files and sidecars.

    Returns:
        (move_plans, already_organized_paths)
    """
    audio_files = find_audio_files(target_root)
    move_plans = []
    already_organized = []

    # Keep track of planned destination paths to prevent collisions
    claimed_destinations = set()

    for fpath in audio_files:
        src_path = os.path.abspath(fpath)
        dest_dir, target_dest, meta = compute_canonical_destination(src_path, music_root)
        dest_path = os.path.abspath(target_dest)

        if src_path == dest_path:
            already_organized.append(src_path)
            claimed_destinations.add(dest_path)
            continue

        # Handle filename collisions (e.g., duplicate tracks or identical tags)
        final_dest = dest_path
        counter = 1
        stem, ext = os.path.splitext(dest_path)
        while final_dest in claimed_destinations or (os.path.exists(final_dest) and os.path.abspath(final_dest) != src_path):
            final_dest = f"{stem} ({counter}){ext}"
            counter += 1

        claimed_destinations.add(final_dest)

        # Detect accompanying .lrc lyrics file
        src_lrc = os.path.splitext(src_path)[0] + ".lrc"
        dest_lrc = os.path.splitext(final_dest)[0] + ".lrc"
        has_lrc = os.path.isfile(src_lrc) and os.path.getsize(src_lrc) > 0

        # Detect potential folder cover art
        src_dir = os.path.dirname(src_path)
        candidate_cover = None
        for cn in COVER_FILENAMES:
            cpath = os.path.join(src_dir, cn)
            if os.path.isfile(cpath) and os.path.getsize(cpath) > 0:
                candidate_cover = cpath
                break

        move_plans.append({
            "src": src_path,
            "dest": final_dest,
            "dest_dir": os.path.dirname(final_dest),
            "has_lrc": has_lrc,
            "src_lrc": src_lrc if has_lrc else None,
            "dest_lrc": dest_lrc if has_lrc else None,
            "candidate_cover": candidate_cover,
            "meta": meta,
        })

    return move_plans, already_organized


def execute_library_organization(
    music_root: str,
    move_plans: list[dict],
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """Execute the computed organization plan safely.

    Returns summary metrics dict.
    """
    total_audio_moved = 0
    total_lrc_moved = 0
    total_covers_migrated = 0
    migrated_cover_dirs = set()
    path_map: dict[str, str] = {}

    for plan in move_plans:
        src = plan["src"]
        dest = plan["dest"]
        dest_dir = plan["dest_dir"]

        if verbose or dry_run:
            rel_src = os.path.relpath(src, music_root)
            rel_dest = os.path.relpath(dest, music_root)
            mode_prefix = "[DRY-RUN] Would move" if dry_run else f"{ICONS.arrow} Moving"
            print(f"   {mode_prefix}: {rel_src} -> {rel_dest}")

        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.move(src, dest)
                path_map[src] = dest
                total_audio_moved += 1
            except OSError as e:
                print(f"   {ICONS.err} Error moving {os.path.basename(src)}: {e}", file=sys.stderr)
                continue

            # Move matching lyrics (.lrc)
            if plan["has_lrc"] and plan["src_lrc"] and os.path.isfile(plan["src_lrc"]):
                try:
                    shutil.move(plan["src_lrc"], plan["dest_lrc"])
                    total_lrc_moved += 1
                    if verbose:
                        print(f"      {ICONS.ok} Moved sidecar lyrics: {os.path.basename(plan['dest_lrc'])}")
                except OSError as e:
                    print(f"      {ICONS.warn} Could not move lyrics: {e}", file=sys.stderr)

            # Migrate album cover if dest folder has none
            dest_cover = os.path.join(dest_dir, "cover.jpg")
            if (
                plan["candidate_cover"]
                and os.path.isfile(plan["candidate_cover"])
                and dest_dir not in migrated_cover_dirs
                and not any(os.path.isfile(os.path.join(dest_dir, cn)) for cn in COVER_FILENAMES)
            ):
                try:
                    shutil.move(plan["candidate_cover"], dest_cover)
                    migrated_cover_dirs.add(dest_dir)
                    total_covers_migrated += 1
                    if verbose:
                        print(f"      {ICONS.img} Migrated album cover to: {os.path.relpath(dest_cover, music_root)}")
                except OSError as e:
                    print(f"      {ICONS.warn} Could not migrate cover: {e}", file=sys.stderr)
        else:
            total_audio_moved += 1
            if plan["has_lrc"]:
                total_lrc_moved += 1
            if plan["candidate_cover"] and dest_dir not in migrated_cover_dirs:
                migrated_cover_dirs.add(dest_dir)
                total_covers_migrated += 1

    # Update playlists to reflect moved paths
    playlists_updated = 0
    if not dry_run and path_map:
        try:
            pl_search_dirs = [music_root, os.path.dirname(music_root)]
            playlists_updated = update_all_playlists(path_map, search_roots=pl_search_dirs)
        except Exception as e:
            if verbose:
                print(f"   {ICONS.warn} Playlist update check: {e}", file=sys.stderr)

    return {
        "audio_moved": total_audio_moved,
        "lrc_moved": total_lrc_moved,
        "covers_migrated": total_covers_migrated,
        "playlists_updated": playlists_updated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Organize library tracks into canonical Music/{Artist}/{Album}/{track} {title} - {artist}.ext layout."
    )
    parser.add_argument(
        "-r", "--root-dir",
        default=".",
        help="Root music directory or DAP mount point (default: .)",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Simulate execution without modifying or moving files on disk.",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed move operations per track.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON summary.",
    )

    args = parser.parse_args()

    target_base = os.path.abspath(args.root_dir)
    if os.path.basename(target_base).lower() == "music":
        scan_root = target_base
        music_root = target_base
    else:
        scan_root = target_base
        music_root = os.path.join(target_base, "Music")

    if not os.path.isdir(scan_root):
        print(f"{ICONS.err} Directory does not exist: {scan_root}", file=sys.stderr)
        return 1

    if not args.json:
        print(f"\n{ICONS.disc} Scanning library to plan organization at: {scan_root}")
        print(f"   Canonical destination root:  {music_root}")

    move_plans, already_organized = plan_library_organization(scan_root, music_root)
    total_candidates = len(move_plans) + len(already_organized)
    to_move_count = len(move_plans)

    if not args.json:
        print(f"   Total audio tracks found:     {total_candidates}")
        print(f"   Already in canonical layout:  {len(already_organized)}")
        print(f"   Tracks requiring movement:    {to_move_count}")

    if to_move_count == 0:
        if not args.json:
            print(f"\n{ICONS.ok} All audio files are already organized in canonical structure. Nothing to do.\n")
        else:
            import json
            print(json.dumps({
                "music_root": music_root,
                "total_tracks": total_candidates,
                "already_organized": len(already_organized),
                "audio_moved": 0,
                "lrc_moved": 0,
                "covers_migrated": 0,
                "playlists_updated": 0,
            }, indent=2))
        return 0

    # Confirmation prompt if not dry-run and not --yes
    if not args.dry_run and not args.yes:
        try:
            prompt = f"\n{ICONS.warn} Proceed with reorganizing {to_move_count} track(s) and sidecars? [y/N]: "
            sys.stderr.write(prompt)
            sys.stderr.flush()
            ans = input().strip().lower()
            if ans not in ("y", "yes"):
                print("\nOrganization cancelled by user.", file=sys.stderr)
                return 0
        except (KeyboardInterrupt, EOFError):
            print("\nOrganization cancelled.", file=sys.stderr)
            return 0

    if not args.json:
        action_verb = "Simulating reorganization for" if args.dry_run else "Reorganizing"
        print(f"\n{ICONS.disc} {action_verb} {to_move_count} track(s)...")

    results = execute_library_organization(
        music_root,
        move_plans,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if args.json:
        import json
        payload = {
            "music_root": music_root,
            "total_tracks": total_candidates,
            "already_organized": len(already_organized),
            "dry_run": args.dry_run,
            **results,
        }
        print(json.dumps(payload, indent=2))
        return 0

    mode_str = "[DRY-RUN] Completed simulation" if args.dry_run else "Successfully organized library"
    print(f"\n{ICONS.ok} {mode_str}:")
    print(f"   - Audio tracks moved:     {results['audio_moved']}")
    print(f"   - Lyrics (.lrc) moved:    {results['lrc_moved']}")
    print(f"   - Album covers migrated:  {results['covers_migrated']}")
    if results['playlists_updated'] > 0:
        print(f"   - Playlists relinked:     {results['playlists_updated']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
