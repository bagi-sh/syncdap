#!/usr/bin/env python3
# ==============================================================================
# Module: src/modules/search.py
# Purpose: Search track/album by name without URL via iTunes & MusicBrainz APIs
# ==============================================================================

import json
import os
import sys
import urllib.parse
import urllib.request


def search_itunes(query: str, entity: str = "song") -> list[dict]:
    """Search iTunes for songs or albums."""
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({
        'term': query,
        'entity': entity,
        'limit': 5
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'SyncDAP/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])
            candidates = []
            for r in results:
                cover = r.get('artworkUrl100', '')
                if cover:
                    # Upgrade to higher resolution artwork
                    cover = cover.replace('100x100bb', '600x600bb')
                candidates.append({
                    'artist': r.get('artistName', ''),
                    'name': r.get('trackName', r.get('collectionName', '')),
                    'album_name': r.get('collectionName', ''),
                    'track_number': r.get('trackNumber', 1),
                    'tracks_count': r.get('trackCount', 1),
                    'year': str(r.get('releaseDate', ''))[:4],
                    'duration': (r.get('trackTimeMillis') or 0) / 1000.0,
                    'cover_url': cover,
                    'genres': [r.get('primaryGenreName', '')],
                    'isrc': r.get('isrc', '')
                })
            return candidates
    except Exception:
        return []


def resolve_query(query: str, is_album: bool = False) -> dict | None:
    """Resolve a text query to canonical metadata."""
    entity = "album" if is_album else "song"
    candidates = search_itunes(query, entity=entity)
    if not candidates and is_album:
        # Fallback to song search if album search returned nothing
        candidates = search_itunes(query, entity="song")

    if not candidates:
        return None

    return candidates[0]


def main():
    if len(sys.argv) < 2:
        print("Usage: search.py <query> [--album] [--json]")
        sys.exit(1)

    query = sys.argv[1]
    is_album = "--album" in sys.argv
    as_json = "--json" in sys.argv

    meta = resolve_query(query, is_album=is_album)
    if not meta:
        print(f"❌ No matching music found for query: '{query}'", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps([meta], indent=2))
    else:
        print(f"✅ Found: {meta['artist']} - {meta['name']} (Album: {meta['album_name']}, {meta['year']})")
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
