# Chapter 7.2: Universal Audio Metadata Abstraction (`audio.py`)

> **The Syncdap Book Navigation:** [← Previous Section](01-architecture.md) • [Table of Contents](../index.md) • [Next Section →](03-text-sanitization.md)

---

## Pedagogical Context & Prerequisites
In Chapter 7.1, we introduced `src/share/` as the foundational utility layer. Here, we inspect `src/share/audio.py`, the core engine responsible for reading, extracting, and writing audio metadata across container formats without leaking format-specific complexity into upper layers.

---

## 1. Universal Metadata Schema & Mutagen Wrapping

Rather than requiring each caller to distinguish between ID3v2 frames, Vorbis comment vectors, and MP4 atoms, `read_audio_metadata()` provides a normalized dictionary contract:

```python
# From src/share/audio.py
def read_audio_metadata(file_path: str, fallback_to_filename: bool = True) -> dict:
    """
    Universally extract tags, embedded URLs, and front cover art from an audio file.
    Returns dict with keys: artist, title, album, album_artist, track_num,
    total_tracks, year, genre, duration, spotify_url, youtube_url, cover_data, cover_mime.
    """
```

### Format Mapping Matrix

| Logical Tag | MP3 (ID3v2.3) | FLAC / OGG / Opus (Vorbis) | M4A / AAC (MP4) | WAV (ID3 / INFO) |
|---|---|---|---|---|
| `title` | `TIT2` | `TITLE` | `©nam` | `TIT2` / `INAM` |
| `artist` | `TPE1` | `ARTIST` | `©ART` | `TPE1` / `IART` |
| `album` | `TALB` | `ALBUM` | `©alb` | `TALB` / `IPRD` |
| `album_artist` | `TPE2` | `ALBUMARTIST` | `aART` | `TPE2` |
| `track_num` | `TRCK` (`"3/12"`) | `TRACKNUMBER` | `trkn` (`[(3, 12)]`) | `TRCK` |
| `genre` | `TCON` | `GENRE` | `©gen` | `TCON` / `IGNR` |

---

## 2. Strict ID3v2.3 UTF-16 BOM Enforcement

As established in Chapter 2.1, older Rockbox firmware revisions crash or fail to index non-ASCII strings encoded in ID3v2.4 UTF-8. When persisting MP3 metadata, `audio.py` enforces ID3v2.3 with Byte Order Mark (BOM) UTF-16:

```python
# From src/share/audio.py
tags.add(TIT2(encoding=1, text=[clean_val(title)]))       # encoding 1 = UTF-16 with BOM
tags.add(TPE1(encoding=1, text=[clean_val(artist)]))
tags.add(TPE2(encoding=1, text=[clean_val(album_artist)]))
tags.add(TALB(encoding=1, text=[clean_val(album)]))
tags.save(file_path, v2_version=3)                         # Enforce ID3v2.3 specification
```

---

## 3. Recursive Audio File Discovery & Ignored Boundaries

`find_audio_files(root_dir)` traverses directory trees while strictly ignoring non-audio directories and portable system partitions:

```python
# From src/share/audio.py
for dirpath, dirnames, filenames in os.walk(root_path):
    dirnames[:] = [
        d for d in dirnames
        if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')
    ]
```

- **Safety Guarantee:** Automatically skips `.rockbox`, `.Trash-1000`, `LOST.DIR`, and system volume caches to avoid corrupting firmware internal states.

---

## Summary & Next Steps
`audio.py` guarantees consistent metadata manipulation across all audio codecs. In the next section, we study `src/share/text.py`, which sanitizes filenames and resolves string matching across FAT32 volume limitations.

---

> **The Syncdap Book Navigation:** [← Previous Section](01-architecture.md) • [Table of Contents](../index.md) • [Next Section →](03-text-sanitization.md)
