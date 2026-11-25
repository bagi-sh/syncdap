# Chapter 4.3: MusicBrainz & Cover Art Archive: The Open Database

> **The Syncdap Book Navigation:** [← Previous Section](02-itunes.md) • [Table of Contents](../index.md) • [Next Section →](04-lrclib.md)

---

## Pedagogical Context & Prerequisites
MusicBrainz provides community-curated, authoritative discographical metadata. Here, we analyze its rate-limiting constraints, User-Agent policies, and Cover Art Archive integration.

---

`syncdap` integrates with the MusicBrainz XML/JSON Web Service (`src/share/api.py`) as a secondary metadata resolver, providing authoritative multi-disc tracklists, acoustic recordings, and genre taxonomy.

---

## 1. Network Protocol & Hard Constraints

- **Base URL:** `https://musicbrainz.org/ws/2/`
- **Format:** Strict JSON (`fmt=json`)
- **HTTP Header:** `User-Agent: SyncDAP/1.0 (info@syncdap.local)` (Mandatory contact URI required by MusicBrainz API terms).
- **Hard Rate Limit:** Exactly **1 request per second** (`time.sleep(1.0)`). Exceeding this rate results in immediate HTTP 503 / IP throttling.
- **Timeout:** `8` seconds.

### Client Implementation
```python
# From src/share/api.py
_UA_MB = 'SyncDAP/1.0 (info@syncdap.local)'

def _mb_get(url: str) -> dict:
    """GET a MusicBrainz JSON endpoint, respecting rate limit."""
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={'User-Agent': _UA_MB})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.load(resp)
```

---

## 2. Multi-Step Album Tracklist Resolution

Because MusicBrainz separates conceptual albums (*Release Groups*) from specific physical or digital releases (*Releases*), `syncdap` executes a 3-step traversal to resolve an album tracklist:

```text
Step 1: Query Release Group
GET /ws/2/release-group/?query=release:"<Album>" AND artist:"<Artist>"&fmt=json&limit=1
          │
          ▼ Extract release-group ID (rg_id)
Step 2: Query Primary Release
GET /ws/2/release/?release-group=<rg_id>&fmt=json&limit=1
          │
          ▼ Extract release ID (rel_id)
Step 3: Query Full Media & Recording Hierarchy
GET /ws/2/release/<rel_id>?inc=recordings&fmt=json
          │
          ▼
Parse multi-disc media entries, track numbers, and millisecond durations
```

### Media Parsing Excerpt
```python
# From src/share/api.py
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
                'duration': dur_ms / 1000.0,
                'total_tracks': len(med_tracks),
            })
```

---

## 3. Genre Extraction & Voting Mechanism

MusicBrainz stores community-submitted tags on releases and artists. In `src/share/api.py`, `musicbrainz_genre()` retrieves tags and genres, selecting the entry with the highest vote count:

```python
# From src/share/api.py
all_tags = (genres or []) + (tags or [])
if all_tags:
    best = max(all_tags, key=lambda t: t.get("count", 0))
    return best.get("name", "").title()
```
This filters out fringe user tags and ensures only high-consensus genre descriptors (e.g. "Progressive Rock", "Post-Bop") are applied to audio files.

---

## Summary & Next Steps
Audio and metadata are now acquired. Next, we examine how timestamped lyric files (`.lrc`) are retrieved from LRCLIB.

---

> **The Syncdap Book Navigation:** [← Previous Section](02-itunes.md) • [Table of Contents](../index.md) • [Next Section →](04-lrclib.md)
