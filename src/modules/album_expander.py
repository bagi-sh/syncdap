#!/usr/bin/env python3
"""Album expansion module for unbundling full-album files into authentic individual tracks.

Audits candidate multi-track audio files, queries release tracklists via MusicBrainz/Deezer,
downloads discrete tracks concurrently, enriches Rockbox ID3 tags, and migrates playlists.
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from share import (
    AUDIO_EXTENSIONS,
    find_audio_files,
    get_audio_metadata,
    get_file_duration,
    sanitize_filename,
    get_track_duration,
    get_album_tracklist,
    is_valid_audio,
    audio_quality_wins,
    track_number_from_filename,
    expand_playlist_entries,
    parse_filename_metadata,
)
from share.icons import ICONS
from modules import fallback, covers, genres, rockbox_tags


@dataclass
class TrackSpec:
    number: int
    title: str
    artist: str
    album: str
    album_artist: str
    duration_sec: float
    year: str = ""
    genre: str = ""
    cover_url: str = ""
    disc_number: int = 1
    total_tracks: int = 1


@dataclass
class BundledCandidate:
    old_path: str
    actual_duration: float
    expected_duration: float
    artist: str
    album: str
    title: str
    fmt: str


def find_bundled_albums(
    root_dir: str,
    target_file: str | None = None,
    forced_format: str | None = None,
) -> list[BundledCandidate]:
    """
    Scan library or single file to identify full-album rip anomalies
    where the physical audio duration drastically exceeds the individual track duration.
    """
    candidates = []

    if target_file and os.path.isfile(target_file):
        files_to_check = [os.path.abspath(target_file)]
    else:
        files_to_check = find_audio_files(root_dir)

    print(f"\n{ICONS.find} Auditing {len(files_to_check)} file(s) for bundled album anomalies...")

    for fpath in files_to_check:
        meta = get_audio_metadata(fpath)
        dur = meta.get('duration') or get_file_duration(fpath)
        artist = meta.get('artist') or ""
        album = meta.get('album') or ""
        title = meta.get('title') or ""

        # Fallback parsing from filename if tags are empty
        if not title or not artist:
            parsed = parse_filename_metadata(fpath)
            artist = artist or parsed.get('artist') or "Unknown Artist"
            album = album or parsed.get('album') or "Unknown Album"
            title = title or parsed.get('title') or os.path.splitext(os.path.basename(fpath))[0]

        is_target = bool(target_file and os.path.abspath(fpath) == os.path.abspath(target_file))
        is_album_title_match = bool(title and album and title.strip().lower() == album.strip().lower())

        # Fast threshold filter: skip tracks < 12m unless target specified or title == album (> 8m)
        if not is_target:
            if dur < 480:
                continue
            if dur < 720 and not is_album_title_match:
                continue

        # Query expected canonical duration for this track title
        expected_sec, source = get_track_duration(artist, title)

        if expected_sec and expected_sec > 0:
            ratio = dur / expected_sec
            if ratio > 2.2 or (is_target and ratio > 1.5):
                fmt = forced_format or os.path.splitext(fpath)[1].lstrip('.').lower() or "mp3"
                candidates.append(
                    BundledCandidate(
                        old_path=fpath,
                        actual_duration=dur,
                        expected_duration=expected_sec,
                        artist=artist,
                        album=album or title,
                        title=title,
                        fmt=fmt,
                    )
                )
                print(f"   {ICONS.warn} Found bundled album: {artist} - {album or title} "
                      f"({dur/60:.1f} min vs expected {expected_sec/60:.1f} min, {ratio:.1f}x)")
        elif is_target and dur >= 480:
            fmt = forced_format or os.path.splitext(fpath)[1].lstrip('.').lower() or "mp3"
            candidates.append(
                BundledCandidate(
                    old_path=fpath,
                    actual_duration=dur,
                    expected_duration=dur,
                    artist=artist,
                    album=album or title,
                    title=title,
                    fmt=fmt,
                )
            )
            print(f"   {ICONS.info} Targeted candidate: {artist} - {album or title} ({dur/60:.1f} min)")

    return candidates


def fetch_official_tracklist(artist: str, album: str) -> list[TrackSpec] | None:
    """Fetch complete tracklist specifications from online metadata."""
    raw_tracks = get_album_tracklist(artist, album)
    if not raw_tracks:
        return None

    specs = []
    total = len(raw_tracks)
    for i, t in enumerate(raw_tracks, 1):
        num = t.get('number') or i
        title = t.get('title') or f"Track {num:02d}"
        dur = t.get('duration') or 0.0
        specs.append(
            TrackSpec(
                number=int(num),
                title=title,
                artist=t.get('artist') or artist,
                album=t.get('album') or album,
                album_artist=t.get('album_artist') or artist,
                duration_sec=float(dur),
                year=t.get('year') or "",
                genre=t.get('genre') or "",
                cover_url=t.get('cover_url') or "",
                disc_number=int(t.get('disc_number') or 1),
                total_tracks=int(t.get('total_tracks') or total),
            )
        )
    return specs


def find_existing_track_in_folder(
    target_dir: str,
    track_num: int,
    exclude_path: str | None = None,
) -> str | None:
    """Find any audio file in target_dir that matches the given track number."""
    if not os.path.isdir(target_dir):
        return None
    exclude_abs = os.path.abspath(exclude_path) if exclude_path else None
    for f in sorted(os.listdir(target_dir)):
        ext = os.path.splitext(f)[1].lower()
        if ext not in AUDIO_EXTENSIONS:
            continue
        full_path = os.path.join(target_dir, f)
        if exclude_abs and os.path.abspath(full_path) == exclude_abs:
            continue
        if track_number_from_filename(f) == track_num:
            return full_path
    return None


def download_single_track(
    track: TrackSpec,
    target_dir: str,
    fmt: str,
    synced_only: bool = False,
    candidate_old_path: str | None = None,
) -> str | None:
    """
    Download single track with quality-aware replacement against existing files in folder.
    - If a track already exists and has better/equal quality: skips download and keeps incumbent.
    - If a track exists with lower quality: downloads new format, replaces incumbent and removes old.
    - If no track exists: downloads directly.
    """
    clean_title = sanitize_filename(track.title)
    clean_artist = sanitize_filename(track.artist)
    filename = f"{track.number:02d} {clean_title} - {clean_artist}.{fmt}"
    out_path = os.path.join(target_dir, filename)

    existing = find_existing_track_in_folder(target_dir, track.number, exclude_path=candidate_old_path)
    if existing and is_valid_audio(existing):
        # We simulate candidate path to evaluate quality
        temp_candidate = out_path
        upgrade, reason = audio_quality_wins(temp_candidate, existing)
        if not upgrade:
            print(f"   {ICONS.info} Keeping existing higher/equal quality track: {os.path.basename(existing)} [{reason}]")
            # Ensure lyrics are present for the existing track
            base_existing, _ = os.path.splitext(existing)
            lrc_existing = f"{base_existing}.lrc"
            if not os.path.exists(lrc_existing):
                fallback.fetch_lyrics(track.artist, track.title, track.album, track.duration_sec, lrc_existing, synced_only)
            return existing

    # Download track
    success = fallback.rescue_single_track(
        artist=track.artist,
        album=track.album,
        title=track.title,
        track_num=track.number,
        tracks_count=track.total_tracks,
        year=track.year,
        genre=track.genre,
        cover_url=track.cover_url,
        expected_duration=track.duration_sec,
        output_path=out_path,
        target_ext=fmt,
        synced_only=synced_only,
    )

    if success and is_valid_audio(out_path):
        # If an existing track existed with inferior quality and different path, remove it cleanly
        if existing and os.path.abspath(existing) != os.path.abspath(out_path):
            try:
                os.remove(existing)
                old_lrc = os.path.splitext(existing)[0] + ".lrc"
                if os.path.isfile(old_lrc):
                    os.remove(old_lrc)
                print(f"   {ICONS.ok} Upgraded quality: replaced {os.path.basename(existing)} with {os.path.basename(out_path)}")
            except Exception as e:
                print(f"   {ICONS.warn} Could not remove superseded file {existing}: {e}")
        return out_path
    return None


def process_candidate(
    candidate: BundledCandidate,
    threads: int = 4,
    dry_run: bool = False,
    synced_only: bool = False,
) -> tuple[str, list[str]] | None:
    """
    Process a single bundled candidate:
    1. Fetch official tracklist
    2. In dry_run mode: display plan and return
    3. Re-download tracks in parallel
    4. Validate >= 80% success
    5. Run enrichment pipeline (rockbox_tags, covers, genres)
    6. Safely remove old bundled rip and orphan .lrc
    Returns (old_path, downloaded_paths) or None
    """
    print(f"\n{ICONS.disc} Resolving official tracklist for: {candidate.artist} - {candidate.album}")
    tracks = fetch_official_tracklist(candidate.artist, candidate.album)
    if not tracks:
        print(f"   {ICONS.err} Could not find official tracklist for '{candidate.artist} - {candidate.album}'. Skipping.")
        return None

    target_dir = os.path.dirname(os.path.abspath(candidate.old_path))
    total_tracks = len(tracks)
    print(f"   {ICONS.info} Found {total_tracks} track(s) in official release:")
    for t in tracks:
        dur_str = f"{int(t.duration_sec)//60}:{int(t.duration_sec)%60:02d}" if t.duration_sec else "--:--"
        print(f"      {t.number:02d}. {t.title} ({dur_str})")

    if dry_run:
        print(f"\n   [DRY-RUN] Would download {total_tracks} track(s) in {candidate.fmt.upper()} to: {target_dir}")
        print(f"   [DRY-RUN] Would remove bundled album file: {candidate.old_path}")
        return (candidate.old_path, [])

    print(f"\n{ICONS.dl} Downloading {total_tracks} track(s) using {threads} parallel worker(s)...")
    downloaded: list[str] = []

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {
            pool.submit(download_single_track, t, target_dir, candidate.fmt, synced_only, candidate.old_path): t
            for t in tracks
        }
        for f in as_completed(futures):
            res = f.result()
            if res:
                downloaded.append(res)
                print(f"   {ICONS.ok} Saved: {os.path.basename(res)}")
            else:
                t = futures[f]
                print(f"   {ICONS.warn} Failed to retrieve: {t.number:02d} - {t.title}")

    # Safety threshold: at least 80% (or all if <= 2 tracks) must succeed
    required_count = max(1, int(total_tracks * 0.8)) if total_tracks > 2 else total_tracks
    if len(downloaded) < required_count:
        print(f"   {ICONS.err} Safety check failed: Only {len(downloaded)}/{total_tracks} tracks succeeded (needed {required_count}).")
        print(f"      Keeping original bundled file intact: {candidate.old_path}")
        return None

    downloaded.sort()

    # Post-processing enrichment pipeline (DRY: reusing existing modules!)
    print(f"\n{ICONS.info} Running metadata enrichment and optimization pipeline...")

    # 1. Rockbox tags normalization
    try:
        rockbox_tags.sanitize_rockbox_metadata(target_dir, dry_run=False)
    except Exception as e:
        print(f"   {ICONS.warn} Rockbox tag normalization warning: {e}")

    # 2. Covers optimization (extract cover.jpg, strip embeds for Rockbox)
    try:
        covers.process_optimize_album(1, 1, target_dir)
    except Exception as e:
        print(f"   {ICONS.warn} Covers optimization warning: {e}")

    # 3. Genres enrichment
    try:
        genres.process_album(1, 1, target_dir)
    except Exception as e:
        print(f"   {ICONS.warn} Genres enrichment warning: {e}")

    # 4. Safe purge of old bundled album file and orphan .lrc
    old_p = os.path.abspath(candidate.old_path)
    base_no_ext, _ = os.path.splitext(old_p)
    old_lrc = f"{base_no_ext}.lrc"

    print(f"\n{ICONS.info} Safely removing old bundled file: {os.path.basename(old_p)}")
    try:
        if os.path.isfile(old_p):
            os.remove(old_p)
    except Exception as e:
        print(f"   {ICONS.warn} Could not remove {old_p}: {e}")

    if os.path.isfile(old_lrc):
        try:
            os.remove(old_lrc)
            print(f"   {ICONS.info} Removed bundled .lrc: {os.path.basename(old_lrc)}")
        except Exception:
            pass

    return (old_p, downloaded)


def expand_albums(
    root_dir: str = ".",
    target_file: str | None = None,
    threads: int = 4,
    dry_run: bool = False,
    assume_yes: bool = False,
    fmt: str | None = None,
    synced_only: bool = False,
) -> int:
    """Main entry point for expanding bundled albums into individual tracks."""
    candidates = find_bundled_albums(root_dir, target_file, fmt)
    if not candidates:
        print(f"\n{ICONS.ok} No bundled full-album anomalies detected.")
        return 0

    print(f"\n{ICONS.disc} Found {len(candidates)} bundled album candidate(s) to expand.")
    for i, c in enumerate(candidates, 1):
        print(f"   [{i}] {c.artist} - {c.album} ({c.actual_duration/60:.1f} min) -> {c.old_path}")

    if not assume_yes and not dry_run:
        try:
            resp = input("\nProceed with album expansion? [Y/n]: ").strip().lower()
            if resp not in ('', 'y', 'yes', 's', 'sim'):
                print("Operation aborted by user.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 0

    migration_map: dict[str, list[str]] = {}
    for cand in candidates:
        result = process_candidate(cand, threads=threads, dry_run=dry_run, synced_only=synced_only)
        if result and result[1]:
            migration_map[result[0]] = result[1]

    # Patch playlists (1-to-N replacement)
    if migration_map and not dry_run:
        print(f"\n{ICONS.pl} Patching playlists for {len(migration_map)} expanded album(s)...")
        updated_pls = expand_playlist_entries(root_dir, migration_map)
        print(f"   {ICONS.ok} Updated {updated_pls} playlist(s) to reference individual tracks.")

    print(f"\n{ICONS.ok} Album expansion complete!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Expand single-file full-album rips into authentic individual tracks via orchestrated re-download."
    )
    parser.add_argument("target_file", nargs="?", default=None, help="Specific bundled audio file to expand (optional).")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music library path to scan (default: .).")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Worker thread concurrency (default: 4).")
    parser.add_argument("-n", "-d", "--dry-run", action="store_true", help="Simulate expansion without downloading or deleting files.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts.")
    parser.add_argument("-F", "--format", default=None, help="Audio format: flac, mp3, m4a, opus, ogg, wav.")
    parser.add_argument("--synced-only", action="store_true", help="Only download synchronized [.lrc] lyrics.")
    args = parser.parse_args()

    sys.exit(
        expand_albums(
            root_dir=args.root_dir,
            target_file=args.target_file,
            threads=args.threads,
            dry_run=args.dry_run,
            assume_yes=args.yes,
            fmt=args.format,
            synced_only=args.synced_only,
        )
    )


if __name__ == "__main__":
    main()
