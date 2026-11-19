#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/audit.py
# Purpose: Audit library files >10 min against iTunes/MusicBrainz to detect
#          accidental full-album rips.
# ==============================================================================

import argparse
import json
import os
import subprocess
import sys

from share import find_audio_files, get_audio_metadata, get_track_duration, format_duration


def audit_long_tracks(
    music_root: str,
    threshold_seconds: float = 600.0,
    json_output: bool = False,
    auto_split: bool = False,
) -> tuple[list[str], int, int, int]:
    """
    Scan music_root for tracks longer than threshold_seconds and verify against APIs.
    Returns (suspect_paths, verified_count, suspect_count, unknown_count).
    Only files with ratio > 1.5x (100% sure full-album rip) are auto-split.
    """
    print(f"\n🔍 Scanning for tracks longer than {threshold_seconds/60:.0f} minutes in: {music_root}")
    audio_files = find_audio_files(music_root)
    long_tracks = []

    for fpath in audio_files:
        meta = get_audio_metadata(fpath)
        dur = meta.get('duration') or 0.0
        if dur >= threshold_seconds:
            long_tracks.append((fpath, meta, dur))

    total = len(long_tracks)
    if total == 0:
        print(f"   ✨ No tracks longer than {threshold_seconds/60:.0f} minutes found in library.")
        return [], 0, 0, 0

    print(f"   Found {total} track(s) >= {threshold_seconds/60:.0f} min. Auditing against metadata APIs...\n")
    print(f"{'STATUS':<20} | {'DURATION':<9} | {'EXPECTED':<9} | {'RATIO':<6} | {'TRACK':<40}")
    print("-" * 95)

    suspect_paths: list[str] = []
    suspect_count  = 0
    verified_count = 0
    unknown_count  = 0

    for fpath, meta, local_dur in long_tracks:
        artist = meta.get('artist') or "Unknown Artist"
        title  = meta.get('title') or os.path.basename(fpath)
        track_label = f"{artist} - {title}"
        if len(track_label) > 38:
            track_label = track_label[:35] + "..."

        expected_dur, source = get_track_duration(artist, title)

        if expected_dur is not None and expected_dur > 0:
            ratio     = local_dur / expected_dur
            local_fmt = format_duration(local_dur)
            exp_fmt   = format_duration(expected_dur)

            if ratio > 1.5:
                status = "🚨 FULL-ALBUM RIP"
                suspect_count += 1
                suspect_paths.append(fpath)
            elif ratio < 0.7:
                status = "⚠️  TRUNCATED"
                suspect_count += 1
            else:
                status = "✅ VERIFIED TRACK"
                verified_count += 1

            print(f"{status:<20} | {local_fmt:<9} | {exp_fmt:<9} | {ratio:<6.1f}x | {track_label:<40}")

            if ratio > 1.5:
                print(f"   ↳ Suggestion: syncdap --expand-albums \"{fpath}\"")
                if auto_split:
                    print(f"   ⚡ Auto-expanding: {fpath}")
                    expander_script = os.path.join(os.path.dirname(__file__), "album_expander.py")
                    try:
                        subprocess.run([sys.executable, expander_script, "-y", fpath], check=True)
                        print(f"   ✅ Auto-expansion complete.")
                    except subprocess.CalledProcessError as e:
                        print(f"   ⚠️  Auto-expansion failed: {e}")
        else:
            unknown_count += 1
            local_fmt = format_duration(local_dur)
            print(f"{'❓ UNVERIFIED':<20} | {local_fmt:<9} | {'--:--':<9} | {'N/A':<6} | {track_label:<40}")

    print("-" * 95)
    print(
        f"📊 Audit Summary: {verified_count} verified authentic, "
        f"{suspect_count} suspected album rips/anomalies, "
        f"{unknown_count} unverified out of {total}.\n"
    )
    return suspect_paths, verified_count, suspect_count, unknown_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit library tracks >10 min to detect accidental full-album rips."
    )
    parser.add_argument("-r", "--root-dir", default=".", help="Root music library path to scan.")
    parser.add_argument(
        "-t", "--threshold", type=float, default=600.0,
        help="Duration threshold in seconds (default: 600 = 10 min)."
    )
    parser.add_argument("--json", action="store_true", help="Output suspect file paths as JSON array.")
    parser.add_argument(
        "--auto-expand", "--auto-split", action="store_true", dest="auto_split",
        help="Automatically expand 100%% sure full-album rips (ratio > 1.5x) via re-download."
    )
    args = parser.parse_args()

    suspect_paths, verified_count, suspect_count, unknown_count = audit_long_tracks(
        args.root_dir,
        args.threshold,
        json_output=args.json,
        auto_split=args.auto_split,
    )

    if args.json:
        print(json.dumps(suspect_paths))


if __name__ == "__main__":
    main()
