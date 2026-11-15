#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/audit.py
# Purpose: Audit library files >10min against iTunes/MusicBrainz to detect accidental full-album rips
# ==============================================================================

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from share import find_audio_files, get_audio_metadata


def check_api_duration(artist: str, title: str) -> tuple[float | None, str | None]:
    """
    Query iTunes Search API with fallback to MusicBrainz to find canonical track duration.
    Returns (duration_in_seconds, source_name).
    """
    if not artist or not title:
        return None, None

    # 1. iTunes Search API (fast, reliable, high rate limit)
    try:
        query = f"{artist} {title}"
        url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
            'term': query,
            'entity': 'song',
            'limit': 5
        })
        req = urllib.request.Request(url, headers={'User-Agent': 'SyncDAP/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for r in data.get('results', []):
                r_artist = r.get('artistName', '').lower()
                dur_ms = r.get('trackTimeMillis')
                if dur_ms and (artist.lower() in r_artist or r_artist in artist.lower()):
                    return dur_ms / 1000.0, "iTunes"
    except Exception:
        pass

    # 2. MusicBrainz API fallback (throttled, authoritative)
    try:
        time.sleep(1.0)  # respect 1 req/sec policy
        mb_query = f'recording:"{title}" AND artist:"{artist}"'
        url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode({
            'query': mb_query,
            'fmt': 'json',
            'limit': 3
        })
        req = urllib.request.Request(url, headers={'User-Agent': 'SyncDAP/1.0 (info@syncdap.local)'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for r in data.get('recordings', []):
                dur_ms = r.get('length')
                if dur_ms:
                    return dur_ms / 1000.0, "MusicBrainz"
    except Exception:
        pass

    return None, None


def format_duration(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


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
    suspect_count = 0
    verified_count = 0
    unknown_count = 0

    for fpath, meta, local_dur in long_tracks:
        artist = meta.get('artist') or "Unknown Artist"
        title = meta.get('title') or os.path.basename(fpath)
        track_label = f"{artist} - {title}"
        if len(track_label) > 38:
            track_label = track_label[:35] + "..."

        expected_dur, source = check_api_duration(artist, title)

        if expected_dur is not None and expected_dur > 0:
            ratio = local_dur / expected_dur
            local_fmt = format_duration(local_dur)
            exp_fmt = format_duration(expected_dur)

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
                print(f"   ↳ Suggestion: syncdap --split \"{fpath}\"")
                if auto_split:
                    print(f"   ⚡ Auto-splitting: {fpath}")
                    split_script = os.path.join(os.path.dirname(__file__), "split.py")
                    try:
                        subprocess.run([sys.executable, split_script, fpath], check=True)
                        print(f"   ✅ Auto-split complete.")
                    except subprocess.CalledProcessError as e:
                        print(f"   ⚠️  Auto-split failed: {e}")
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


def main():
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
        "--auto-split", action="store_true",
        help="Automatically run splitter on 100%% sure full-album rips (ratio > 1.5x)."
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
