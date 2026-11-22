#!/usr/bin/env python3
"""Music metadata search module via iTunes Store API.

Searches track or album by text query without requiring external URLs and
formats metadata key-value outputs for shell integration or JSON pipelines.
"""

import json
import sys

from share.api import itunes_song_metadata
from share.icons import ICONS


def resolve_query(query: str, is_album: bool = False) -> dict | None:
    return itunes_song_metadata(query, is_album=is_album)


def main():
    if len(sys.argv) < 2:
        print("Usage: search.py <query> [--album] [--json]", file=sys.stderr)
        sys.exit(2)

    query = sys.argv[1]
    is_album = "--album" in sys.argv
    as_json = "--json" in sys.argv

    meta = resolve_query(query, is_album=is_album)
    if not meta:
        print(f"{ICONS.err} No matching music found for query: '{query}'", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps([meta], indent=2))
    else:
        print(f"{ICONS.ok} Found: {meta['artist']} - {meta['name']} (Album: {meta['album_name']}, {meta['year']})")
        print(f"ARTIST={meta['artist']}")
        print(f"TITLE={meta['name']}")
        print(f"ALBUM={meta['album_name']}")
        print(f"TRACK_NUMBER={meta['track_number']}")
        print(f"TRACKS_COUNT={meta['tracks_count']}")
        print(f"YEAR={meta['year']}")
        print(f"DURATION={meta['duration']}")
        print(f"COVER_URL={meta['cover_url']}")


if __name__ == "__main__":
    main()
