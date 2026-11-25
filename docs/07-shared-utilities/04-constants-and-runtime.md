# Chapter 7.4: System Constants, HTTP Pooling & Terminal Presentation

> **The Syncdap Book Navigation:** [← Previous Section](03-text-sanitization.md) • [Table of Contents](../index.md) • [Next Section →](../08-cli-reference/01-grammar.md)

---

## Pedagogical Context & Prerequisites
In this final section of Chapter 7, we inspect the operational constants (`constants.py`), HTTP client architecture (`api.py`), and terminal presentation formatting (`icons.py`) that establish runtime defaults across `syncdap`.

---

## 1. System Constants & Hardware Thresholds (`constants.py`)

`src/share/constants.py` centralizes all system thresholds:

```python
# From src/share/constants.py
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')
LOSSLESS_EXTENSIONS = ('.flac', '.wav', '.aiff', '.ape', '.alac')
LOSSY_EXTENSIONS = ('.m4a', '.opus', '.ogg', '.mp3')

COVER_NAME = "cover.jpg"
COVER_RESOLUTION = 600
AUDIT_THRESHOLD_SECONDS = 600  # 10 minutes (identifies full-album rips)
```

---

## 2. HTTP Client Pooling & Rate-Limiting Protection (`api.py`)

All network I/O through `src/share/api.py` enforces mandatory User-Agent headers, timeouts, and rate-limiting delays:

```python
# From src/share/api.py
_UA = 'SyncDAP/1.0'
_UA_MB = 'SyncDAP/1.0 (info@syncdap.local)'

def itunes_search(query: str, entity: str = 'song', limit: int = 5) -> list[dict]:
    url = 'https://itunes.apple.com/search?' + urllib.parse.urlencode({
        'term': query, 'entity': entity, 'limit': limit, 'media': 'music'
    })
    req = urllib.request.Request(url, headers={'User-Agent': _UA})
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        return json.load(resp).get('results', [])
```

---

## 3. Monochromatic Terminal Icons & Glyphs (`icons.py`)

`src/share/icons.py` provides Python wrappers for terminal diagnostics, honoring `--icons` or `--no-icons`:

```python
# From src/share/icons.py
ICON_OK = "✔" if ICONS_ENABLED else "[OK]"
ICON_WARN = "⚠" if ICONS_ENABLED else "[WARN]"
ICON_FAIL = "✖" if ICONS_ENABLED else "[FAIL]"
```

---

## Summary & Next Steps
With Chapter 7 complete, you now possess comprehensive knowledge of `syncdap`'s internal engines and shared infrastructure. We conclude the book with Chapter 8: the complete Command-Line Interface and Resource Reference Manual.

---

> **The Syncdap Book Navigation:** [← Previous Section](03-text-sanitization.md) • [Table of Contents](../index.md) • [Next Section →](../08-cli-reference/01-grammar.md)
