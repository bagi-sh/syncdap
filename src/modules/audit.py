"""Library duration anomaly and full-album rip auditor."""

import argparse
import json
import os
import subprocess
import sys

from share import (
    find_audio_files,
    get_audio_metadata,
    get_track_duration,
    format_duration,
    ICONS,
    AUDIT_THRESHOLD_SECONDS,
    AUDIT_RATIO_THRESHOLD,
)


def audit_long_tracks(
    music_root: str,
    threshold_seconds: float = AUDIT_THRESHOLD_SECONDS,
    json_output: bool = False,
    auto_split: bool = False,
    ratio_threshold: float = AUDIT_RATIO_THRESHOLD,
) -> tuple[list[str], int, int, int]:
    """Scan music_root for tracks longer than threshold and verify against APIs.

    Files with ratio > ratio_threshold compared to expected track duration indicate
    full-album single-file rips.
    """
    if not json_output:
        print(f"\n{ICONS.find} Scanning for tracks longer than {threshold_seconds/60:.0f} minutes in: {music_root}")

    audio_files = find_audio_files(music_root)
    long_tracks = []

    for fpath in audio_files:
        meta = get_audio_metadata(fpath)
        dur = meta.get('duration') or 0.0
        if dur >= threshold_seconds:
            long_tracks.append((fpath, meta, dur))

    total = len(long_tracks)
    if total == 0:
        if not json_output:
            print(f"  {ICONS.ok} No tracks longer than {threshold_seconds/60:.0f} minutes found in library.")
        return [], 0, 0, 0

    if not json_output:
        print(f"  {ICONS.info} Found {total} track(s) >= {threshold_seconds/60:.0f} min. Auditing against metadata APIs...\n")
        print(f"{'STATUS':<20} | {'DURATION':<9} | {'EXPECTED':<9} | {'RATIO':<6} | {'TRACK':<40}")
        print("─" * 95)

    suspect_paths: list[str] = []
    suspect_count  = 0
    verified_count = 0
    unknown_count  = 0

    for fpath, meta, local_dur in long_tracks:
        artist = meta.get('artist') or "Unknown Artist"
        title  = meta.get('title') or os.path.basename(fpath)
        track_label = f"{artist} - {title}"
        if len(track_label) > 38:
            track_label = track_label[:35] + ICONS.ellipsis

        expected_dur, source = get_track_duration(artist, title)

        if expected_dur is not None and expected_dur > 0:
            ratio     = local_dur / expected_dur
            local_fmt = format_duration(local_dur)
            exp_fmt   = format_duration(expected_dur)

            if ratio > ratio_threshold:
                status = f"{ICONS.err} FULL-ALBUM RIP"
                suspect_count += 1
                suspect_paths.append(fpath)
            elif ratio < 0.7:
                status = f"{ICONS.warn} TRUNCATED"
                suspect_count += 1
            else:
                status = f"{ICONS.ok} VERIFIED TRACK"
                verified_count += 1

            if not json_output:
                print(f"{status:<20} | {local_fmt:<9} | {exp_fmt:<9} | {ratio:<6.1f}x | {track_label:<40}")

            if ratio > ratio_threshold and not json_output:
                print(f"   {ICONS.arrow} Suggestion: syncdap album expand \"{fpath}\"")
                if auto_split:
                    print(f"   {ICONS.dl} Auto-expanding: {fpath}")
                    expander_script = os.path.join(os.path.dirname(__file__), "album_expander.py")
                    try:
                        subprocess.run([sys.executable, expander_script, "-y", fpath], check=True)
                        print(f"   {ICONS.ok} Auto-expansion complete.")
                    except subprocess.CalledProcessError as e:
                        print(f"   {ICONS.warn} Auto-expansion failed: {e}", file=sys.stderr)
        else:
            unknown_count += 1
            local_fmt = format_duration(local_dur)
            if not json_output:
                print(f"{ICONS.info + ' UNVERIFIED':<20} | {local_fmt:<9} | {'--:--':<9} | {'N/A':<6} | {track_label:<40}")

    if not json_output:
        print("─" * 95)
        print(
            f"Audit Summary: {verified_count} verified, "
            f"{suspect_count} suspected album rips, "
            f"{unknown_count} unverified out of {total}.\n"
        )
    return suspect_paths, verified_count, suspect_count, unknown_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit library tracks >10 min to detect accidental full-album rips."
    )
    parser.add_argument("-r", "--root-dir", default=None, help="Root music library path to scan (default: .).")
    parser.add_argument(
        "-t", "--threshold", type=float, default=None,
        help=f"Duration threshold in seconds (precedence: CLI -> local config -> {AUDIT_THRESHOLD_SECONDS:.0f}s).",
    )
    parser.add_argument(
        "--ratio", type=float, default=None,
        help=f"Duration ratio threshold to classify full-album rips (precedence: CLI -> local config -> {AUDIT_RATIO_THRESHOLD}x).",
    )
    parser.add_argument("--json", action="store_true", help="Output suspect file paths as JSON array.")
    parser.add_argument(
        "--auto-expand", "--auto-split", action="store_true", dest="auto_split",
        help="Automatically expand confirmed full-album rips (ratio > 1.5x) via re-download."
    )
    args = parser.parse_args()

    # Precedence: 1. CLI flag -> 2. Environment / local config -> 3. Installation default
    threshold = args.threshold if args.threshold is not None else AUDIT_THRESHOLD_SECONDS
    ratio = args.ratio if args.ratio is not None else AUDIT_RATIO_THRESHOLD
    root_dir = args.root_dir if args.root_dir is not None else os.environ.get("SYNCDAP_ROOT_DIR", ".")

    suspect_paths, verified_count, suspect_count, unknown_count = audit_long_tracks(
        root_dir,
        threshold,
        json_output=args.json,
        auto_split=args.auto_split,
        ratio_threshold=ratio,
    )

    if args.json:
        print(json.dumps(suspect_paths))


if __name__ == "__main__":
    main()
