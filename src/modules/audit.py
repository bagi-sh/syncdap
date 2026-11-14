#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/audit.py
# Purpose: Audit library files >10min against iTunes/MusicBrainz to detect accidental full-album rips
# ==============================================================================

import os
import sys
import json
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

    # 1. iTunes Search API (Fast, reliable, high rate limit)
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
                r_title = r.get('trackName', '').lower()
                dur_ms = r.get('trackTimeMillis')
                if dur_ms and (artist.lower() in r_artist or r_artist in artist.lower()):
                    return dur_ms / 1000.0, "iTunes"
    except Exception:
        pass

    # 2. MusicBrainz API fallback (Throttled, authoritative)
    try:
        time.sleep(1.0)  # Respect MusicBrainz 1 req/sec policy
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


def audit_long_tracks(music_root: str, threshold_seconds: float = 600.0):
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
        return 0, 0, 0

    print(f"   Found {total} track(s) >= {threshold_seconds/60:.0f} min. Auditing durations against metadata APIs...\n")
    print(f"{'STATUS':<20} | {'DURATION':<9} | {'EXPECTED':<9} | {'RATIO':<6} | {'TRACK':<40}")
    print("-" * 95)

    suspect_count = 0
    verified_count = 0
    unknown_count = 0

    for idx, (fpath, meta, local_dur) in enumerate(long_tracks, 1):
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
            elif ratio < 0.7:
                status = "⚠️  TRUNCATED"
                suspect_count += 1
            else:
                status = "✅ VERIFIED TRACK"
                verified_count += 1

            print(f"{status:<20} | {local_fmt:<9} | {exp_fmt:<9} | {ratio:<6.1f}x | {track_label:<40}")
            if ratio > 1.5:
                print(f"   ↳ Suggestion: Run 'syncdap --split \"{fpath}\"' to extract individual songs.")
        else:
            unknown_count += 1
            local_fmt = format_duration(local_dur)
            print(f"{'❓ UNVERIFIED':<20} | {local_fmt:<9} | {'--:--':<9} | {'N/A':<6} | {track_label:<40}")

    print("-" * 95)
    print(f"📊 Audit Summary: {verified_count} verified authentic, {suspect_count} suspected album rips/anomalies, {unknown_count} unverified out of {total}.\n")
    return suspect_count, verified_count, unknown_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit library tracks >10 min to detect accidental full-album rips.")
    parser.add_argument("-r", "--root-dir", default=".", help="Root music library path to scan.")
    parser.add_argument("-t", "--threshold", type=float, default=600.0, help="Duration threshold in seconds (default: 600 = 10 min).")
    args = parser.parse_args()

    audit_long_tracks(args.root_dir, args.threshold)


if __name__ == "__main__":
    main()
