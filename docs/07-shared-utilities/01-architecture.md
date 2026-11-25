# Chapter 7.1: Shared Architecture & Package Boundaries (`src/share/`)

> **The Syncdap Book Navigation:** [← Previous Section](../06-specialized-subsystems/04-scrobbler.md) • [Table of Contents](../index.md) • [Next Section →](02-audio-engine.md)

---

## Pedagogical Context & Prerequisites
Chapter 7 explores `src/share/`, the foundational utility package. This opening section establishes its architecture, component ownership, and shared responsibilities.

---

`src/share/` is the core foundation library containing common abstractions, constants, audio tag handlers, string sanitizers, and HTTP client wrappers used across all `syncdap` modules.

---

## 1. Package Structure & Responsibilities

| Module | Core Responsibility |
|---|---|
| `audio.py` | Universal audio tag reader/writer for MP3, FLAC, M4A, OGG, Opus, WAV |
| `text.py` | FAT32/exFAT path sanitization, symbol replacements, and normalized string comparisons |
| `constants.py` | Supported audio extensions, ignored system folders, and regex filters |
| `api.py` | HTTP clients for iTunes, Deezer, and MusicBrainz APIs |
| `covers.py` | Artwork extraction and ID3 `APIC` / FLAC `Picture` manipulation |
| `lyrics.py` | LRCLIB client and `syncedlyrics` fallback wrapper |
| `playlists.py` | M3U8 path parsing and relative directory remapping |
| `config.py` | Python configuration reader for `~/.config/syncdap/` |
| `icons.py` | Monochromatic glyphs and formatted terminal logging |

---

## 2. Universal Audio Metadata Abstraction (`audio.py`)

Rather than having each module interact with format-specific Mutagen classes, `read_audio_metadata()` and `write_audio_metadata()` provide a unified interface:

```python
# From src/share/audio.py
def read_audio_metadata(file_path: str, fallback_to_filename: bool = True) -> dict:
    """
    Universally extract tags, embedded URLs, and front cover art from an audio file.
    Returns dict with keys: artist, title, album, album_artist, track_num,
    total_tracks, year, genre, duration, spotify_url, youtube_url, cover_data, cover_mime.
    """
```

- Transparently maps between ID3v2 frames (`TIT2`, `TPE1`, `TPE2`), Vorbis comments (`TITLE`, `ARTIST`, `ALBUMARTIST`), and MP4 atoms (`©nam`, `©ART`, `aART`).
- Enforces strict ID3v2.3 UTF-16 compatibility when writing MP3 tags.

---

## 3. String Normalization & FAT32 Sanitization (`text.py`)

- `normalize_str(s)`: Strips non-alphanumeric punctuation and lowercases strings for fuzzy matching.
- `sanitize_filename(name, for_folder=False)`: Replaces FAT32-illegal characters (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`) with underscores, replaces full-width Japanese punctuation, and strips trailing periods and spaces.

---

## Summary & Next Steps
Next, we dive into the universal audio metadata engine: `audio.py`.

---

> **The Syncdap Book Navigation:** [← Previous Section](../06-specialized-subsystems/04-scrobbler.md) • [Table of Contents](../index.md) • [Next Section →](02-audio-engine.md)
