# ==============================================================================
# Module: src/share/api.py
# Purpose: Shared API clients for iTunes and MusicBrainz metadata queries
#          Used by: modules/album_expander.py, modules/audit.py, modules/search.py
# ==============================================================================

import json
import re
import time
import urllib.parse
import urllib.request

_UA = 'SyncDAP/1.0'
_UA_MB = 'SyncDAP/1.0 (info@syncdap.local)'

# Suffixes to strip from album names before API search
_ALBUM_EDITION_RE = re.compile(
    r'\s*[\(\[,]\s*(?:deluxe|deluxe edition|super deluxe|remastered|remaster|'
    r'expanded|anniversary|bonus tracks?|special edition|limited edition|'
    r'explicit|clean|instrumental|radio edit|original soundtrack|ost|'
    r'\d{4} remaster|\d+th anniversary)[^\)\]]*[\)\]]?',
    re.IGNORECASE
)


def normalize_album_name(album: str) -> str:
    """Strip edition/remaster suffixes for a cleaner API search query."""
    return _ALBUM_EDITION_RE.sub('', album).strip()


# ==============================================================================
# iTunes Search API
# ==============================================================================

def itunes_search(query: str, entity: str = 'song', limit: int = 5) -> list[dict]:
    """
    Search iTunes. Returns raw result dicts from the API.
    entity: 'song', 'album', 'musicArtist', etc.
    """
    url = 'https://itunes.apple.com/search?' + urllib.parse.urlencode({
        'term': query, 'entity': entity, 'limit': limit, 'media': 'music'
    })
    try:
        req = urllib.request.Request(url, headers={'User-Agent': _UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.load(resp).get('results', [])
    except Exception:
        return []


def itunes_lookup_collection(collection_id: int) -> list[dict]:
    """Fetch track list for an iTunes collection (album) by collectionId."""
    url = f'https://itunes.apple.com/lookup?id={collection_id}&entity=song'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': _UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.load(resp).get('results', [])
    except Exception:
        return []


def itunes_track_duration(artist: str, title: str) -> float | None:
    """Return canonical track duration in seconds from iTunes, or None."""
    for r in itunes_search(f'{artist} {title}', entity='song', limit=5):
        r_artist = r.get('artistName', '').lower()
        dur_ms = r.get('trackTimeMillis')
        if dur_ms and (artist.lower() in r_artist or r_artist in artist.lower()):
            return dur_ms / 1000.0
    return None


def itunes_album_tracklist(artist: str, album: str) -> list[dict] | None:
    """
    Return ordered list of track dicts for an album via iTunes, or None on failure.
    Each dict contains: number, title, artist, album, album_artist, duration,
    disc_number, year, genre, cover_url, total_tracks.
    """
    results = itunes_search(f'{artist} {album}', entity='album', limit=1)
    if not results:
        return None
    collection_id = results[0].get('collectionId')
    if not collection_id:
        return None
    tracks = []
    items = itunes_lookup_collection(collection_id)
    album_cover = results[0].get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    album_artist = results[0].get('artistName', artist)
    album_year = str(results[0].get('releaseDate', ''))[:4]
    album_genre = results[0].get('primaryGenreName', '')

    for t in sorted(items, key=lambda x: (x.get('discNumber', 1), x.get('trackNumber', 0))):
        if t.get('wrapperType') != 'track':
            continue
        title = t.get('trackName')
        dur_ms = t.get('trackTimeMillis')
        if title and dur_ms:
            cover = t.get('artworkUrl100', '').replace('100x100bb', '600x600bb') or album_cover
            tracks.append({
                'number': t.get('trackNumber', len(tracks) + 1),
                'disc_number': t.get('discNumber', 1),
                'title': title,
                'artist': t.get('artistName', artist),
                'album': t.get('collectionName', album),
                'album_artist': t.get('collectionArtistName', album_artist),
                'duration': dur_ms / 1000.0,
                'year': str(t.get('releaseDate', ''))[:4] or album_year,
                'genre': t.get('primaryGenreName', '') or album_genre,
                'cover_url': cover,
                'total_tracks': t.get('trackCount', len(items) - 1),
            })
    return tracks if tracks else None


def itunes_song_metadata(query: str, is_album: bool = False) -> dict | None:
    """
    Resolve a text query to canonical song/album metadata dict, or None.
    Returns the first result with keys: artist, name, album_name, track_number,
    tracks_count, year, duration, cover_url, genres.
    """
    entity = 'album' if is_album else 'song'
    candidates = itunes_search(query, entity=entity, limit=5)
    if not candidates and is_album:
        candidates = itunes_search(query, entity='song', limit=5)
    if not candidates:
        return None
    r = candidates[0]
    cover = r.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    return {
        'artist':       r.get('artistName', ''),
        'name':         r.get('trackName', r.get('collectionName', '')),
        'album_name':   r.get('collectionName', ''),
        'track_number': r.get('trackNumber', 1),
        'tracks_count': r.get('trackCount', 1),
        'year':         str(r.get('releaseDate', ''))[:4],
        'duration':     (r.get('trackTimeMillis') or 0) / 1000.0,
        'cover_url':    cover,
        'genres':       [r.get('primaryGenreName', '')],
        'isrc':         r.get('isrc', ''),
    }


# ==============================================================================
# MusicBrainz API
# ==============================================================================

def _mb_get(url: str) -> dict:
    """GET a MusicBrainz JSON endpoint, respecting rate limit."""
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={'User-Agent': _UA_MB})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.load(resp)


def musicbrainz_track_duration(artist: str, title: str) -> float | None:
    """Return canonical track duration in seconds from MusicBrainz, or None."""
    try:
        mb_q = f'recording:"{title}" AND artist:"{artist}"'
        url = 'https://musicbrainz.org/ws/2/recording/?' + urllib.parse.urlencode({
            'query': mb_q, 'fmt': 'json', 'limit': 3
        })
        data = _mb_get(url)
        for r in data.get('recordings', []):
            dur_ms = r.get('length')
            if dur_ms:
                return dur_ms / 1000.0
    except Exception:
        pass
    return None


def musicbrainz_album_tracklist(artist: str, album: str) -> list[dict] | None:
    """
    Return ordered list of {'title': str, 'duration': float} for an album
    via MusicBrainz (3-step: release-group → release list → recordings), or None.
    """
    try:
        rg_url = 'https://musicbrainz.org/ws/2/release-group/?' + urllib.parse.urlencode({
            'query': f'release:"{album}" AND artist:"{artist}"',
            'fmt': 'json', 'limit': 1
        })
        rg_data = _mb_get(rg_url)
        rg_results = rg_data.get('release-groups', [])
        if not rg_results:
            return None
        rg_id = rg_results[0].get('id')
        if not rg_id:
            return None

        rel_url = 'https://musicbrainz.org/ws/2/release/?' + urllib.parse.urlencode({
            'release-group': rg_id, 'fmt': 'json', 'limit': 1
        })
        releases = _mb_get(rel_url).get('releases', [])
        if not releases:
            return None
        rel_id = releases[0].get('id')

        rec_url = f'https://musicbrainz.org/ws/2/release/{rel_id}?' + urllib.parse.urlencode({
            'inc': 'recordings', 'fmt': 'json'
        })
        rel_data = _mb_get(rec_url)
        tracks = []
        for medium in rel_data.get('media', []):
            disc_pos = medium.get('position', 1)
            med_tracks = medium.get('tracks', [])
            for tr in med_tracks:
                t_title = tr.get('title')
                dur_ms = tr.get('length')
                tr_pos = tr.get('position') or (len(tracks) + 1)
                if t_title and dur_ms:
                    tracks.append({
                        'number': int(tr_pos),
                        'disc_number': int(disc_pos),
                        'title': t_title,
                        'artist': artist,
                        'album': album,
                        'album_artist': artist,
                        'duration': dur_ms / 1000.0,
                        'year': '',
                        'genre': '',
                        'cover_url': '',
                        'total_tracks': len(med_tracks),
                    })
        return tracks if tracks else None
    except Exception:
        return None


# ==============================================================================
# Unified public helpers (iTunes preferred → MusicBrainz fallback)
# ==============================================================================

def get_track_duration(artist: str, title: str) -> tuple[float | None, str | None]:
    """
    Return (duration_seconds, source_name) for a track, or (None, None).
    Tries iTunes first, then MusicBrainz.
    """
    dur = itunes_track_duration(artist, title)
    if dur is not None:
        return dur, 'iTunes'
    dur = musicbrainz_track_duration(artist, title)
    if dur is not None:
        return dur, 'MusicBrainz'
    return None, None


def get_album_tracklist(artist: str, album: str) -> list[dict] | None:
    """
    Return ordered track list for an album.
    Tries iTunes then MusicBrainz for both the original and normalized album name.
    Each dict: {'title': str, 'duration': float}.
    """
    album_variants = [album]
    normalized = normalize_album_name(album)
    if normalized.lower() != album.lower():
        album_variants.append(normalized)

    for album_q in album_variants:
        result = itunes_album_tracklist(artist, album_q)
        if result:
            print(f"   📡 iTunes: found {len(result)} tracks for \"{artist} – {album_q}\"")
            return result

    for album_q in album_variants:
        result = musicbrainz_album_tracklist(artist, album_q)
        if result:
            print(f"   📡 MusicBrainz: found {len(result)} tracks for \"{artist} – {album_q}\"")
            return result

    return None
