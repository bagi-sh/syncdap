# Chapter 5.10: Interactive Metadata Search Engine (`search.py`)

> **The Syncdap Book Navigation:** [← Previous Section](09-genres.md) • [Table of Contents](../index.md) • [Next Section →](11-lyrics.md)

---

## Pedagogical Context & Prerequisites
Here, we inspect `search.py`, the CLI helper used by both human operators and automated scripts to query track and album metadata across multiple upstream services.

---

`src/modules/search.py` queries metadata APIs using unstructured text search queries without requiring Spotify URLs, emitting structured metadata for CLI display or JSON automation.

---

## 1. Resolution Engine

`search.py` queries the iTunes Search API via `src/share/api.py`:
- **Tracks:** Queries `entity="song"`.
- **Albums (`--album`):** Queries `entity="album"`.
- Cleans query strings using `clean_term()` to remove parenthesis and featured artist clutter.

---

## 2. Output Schemas

### Formatted Text (Default)
```text
✓ Found: The Beatles - Come Together (Album: Abbey Road, 1969)
ARTIST=The Beatles
TITLE=Come Together
ALBUM=Abbey Road
TRACK_NUMBER=1
TRACKS_COUNT=17
YEAR=1969
DURATION=259.0
COVER_URL=https://is1-ssl.mzstatic.com/.../600x600bb.jpg
```

### Structured JSON (`--json`)
```json
[
  {
    "artist": "The Beatles",
    "name": "Come Together",
    "album_name": "Abbey Road",
    "track_number": 1,
    "tracks_count": 17,
    "year": "1969",
    "duration": 259.0,
    "cover_url": "https://is1-ssl.mzstatic.com/.../600x600bb.jpg",
    "genres": ["Rock"],
    "isrc": "GBAYE0601498"
  }
]
```

---

## 3. CLI Invocations

```bash
# Search for a track by query
syncdap search "Pink Floyd Comfortably Numb"

# Search for an album specifically
python3 src/modules/search.py "Radiohead OK Computer" --album

# Output machine-readable JSON for scripting
syncdap search "Queen Bohemian Rhapsody" --json
```

---

## Summary & Next Steps
Next, we examine the concurrent lyric fetching engine: `lyrics.py`.

---

> **The Syncdap Book Navigation:** [← Previous Section](09-genres.md) • [Table of Contents](../index.md) • [Next Section →](11-lyrics.md)
