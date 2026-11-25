# Chapter 2.1: The Rockbox Audio & Database Model

> **The Syncdap Book Navigation:** [← Previous Section](../01-getting-started/02-configuration.md) • [Table of Contents](../index.md) • [Next Section →](02-fat32-storage.md)

---

## Pedagogical Context & Prerequisites
Before diving into software implementation, we must understand the physical and firmware environment of our target devices. Rockbox is an open-source replacement firmware operating on constrained hardware (often 32 MB to 64 MB of RAM) with strict tag database indexing rules.

---

Rockbox is an open-source replacement firmware for digital audio players (e.g., Apple iPod Classic/Mini/Video, SanDisk Sansa Clip/Fuze, iRiver H100/H300, and Android/Innioasis DAP ports). It enforces unique hardware, memory, and database constraints that `syncdap` is specifically engineered to satisfy.

---

## 1. Split Album Prevention & `ALBUMARTIST` Invariants

### The Problem
Rockbox builds its internal tag database (`database.db`) by indexing audio files by `ALBUM`. If tracks inside the same directory contain varying `ARTIST` tags (e.g., collaborations, compilations, or featured artists) and lack an identical `ALBUMARTIST` tag:
- Rockbox creates separate, duplicate entries for the album in its database browser (one for each unique artist).
- Track playback order becomes fragmented, breaking gapless playback across album tracks.

### The Mechanism (`src/modules/rockbox_tags.py`)
`syncdap` scans every folder and derives a canonical album artist using a two-tier heuristic:
1. **Directory Structure:** If files are located in `/Music/<Artist>/<Album>/`, `<Artist>` is adopted.
2. **Majority Voting:** If the folder is ambiguous, it inspects existing `ALBUMARTIST` tags or votes on the dominant `ARTIST` tag across all tracks in the folder.

It then writes an identical `ALBUMARTIST` tag across all tracks in the directory:
```python
# From src/modules/rockbox_tags.py
if needs_tag_fix:
    try:
        audio = mutagen.File(file_path, easy=True)
        if audio is not None:
            audio['albumartist'] = [canonical_album_artist]
            audio.save()
    except Exception as e:
        # Non-fatal log, preserves file integrity
        pass
```

---

## 2. Standalone `cover.jpg` vs. Embedded APIC Frames

### DAP Memory Architecture & RAM Constraints
Older digital audio players operate under severe RAM constraints:
- **iPod Classic (5th / 5.5th Gen):** 32 MB or 64 MB of total system RAM.
- **iPod Mini / Nano:** 32 MB of RAM.
- **Sansa Clip Zip / Clip+:** 2 MB to 8 MB of RAM.

When an audio file contains an embedded ID3v2 `APIC` frame or FLAC `Picture` metadata block (often 1 MB to 5 MB per track from high-resolution digital purchases), the DAP must allocate memory to parse and buffer this image on every track transition. Across a 1,000-track library, embedded artwork can consume 2 GB to 5 GB of storage and cause audio stuttering, sluggish menu responsiveness, or out-of-memory kernel panics during database initialization.

### The Solution (`src/modules/covers.py`)
Rockbox natively looks for external artwork in the album directory named `cover.jpg`, `folder.jpg`, or `albumart.jpg`:
1. **Extraction:** `syncdap covers optimize` locates the highest resolution embedded image in the album (or queries iTunes for a 600x600 cover).
2. **External Persistence:** It saves a single `cover.jpg` (or `folder.jpg`) in the album folder.
3. **Stripping:** It strips heavy embedded `APIC` tags from all audio files in that folder, saving ~90% of tag overhead without losing artwork display on the DAP.

---

## 3. ID3v2.3 vs. ID3v2.4 Tag Compatibility

| Standard | Encoding | Rockbox Support | syncdap Behavior |
|---|---|---|---|
| **ID3v2.3** | UTF-16 (`\xFF\xFE`) or ISO-8859-1 | Full native hardware decoding | **Default target** for all tag normalization |
| **ID3v2.4** | UTF-8 (`\x03`) | Inconsistent on older firmware revisions | Automatically transcoded to ID3v2.3 |

### Tag Encoding Verification
Rockbox's ID3 parser expects UTF-16 with Byte Order Mark (BOM) for non-ASCII text. `syncdap` writes ID3v2.3 frames with UTF-16 encoding:
```python
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB

tags = ID3()
tags.add(TIT2(encoding=1, text=["Track Title"]))       # encoding 1 = UTF-16
tags.add(TPE1(encoding=1, text=["Track Artist"]))
tags.add(TPE2(encoding=1, text=["Canonical Album Artist"]))
tags.add(TALB(encoding=1, text=["Album Name"]))
tags.save(file_path, v2_version=3)                    # Enforce ID3v2.3
```

---

## 4. Audioscrobbler Log (`.scrobbler.log`) Invariants & Firmware Quirks

Rockbox logs every played track to a local file named `.scrobbler.log` on the root of the DAP filesystem.

### Log Format Specification
The log file uses the Audioscrobbler Portable Player format (v1.1). The header defines metadata directives, followed by tab-separated track playback records:
```text
#AUDIOSCROBBLER/1.1
#TZ/UNKNOWN
#CLIENT/Rockbox gigabeat 3.15

Artist Name	Album Name	Track Name	1	245	L	1731884400	/Music/Artist/Album/01 Track.mp3
```

Each row contains exactly 8 tab-separated fields:
1. `artist`: String (artist name).
2. `album`: String (album name).
3. `track`: String (track title).
4. `tracknumber`: Integer (or empty/0 if absent).
5. `duration`: Integer (track length in seconds).
6. `rating`: Single character (`L` = Listened, `S` = Skipped). Only `L` records are valid for submission.
7. `timestamp`: Integer (Unix epoch timestamp).
8. `path`: String (absolute DAP filesystem path).

### Documented Firmware Quirks & syncdap Mitigations

#### Quirk 1: Inaccurate `#TZ` Header Directive
- **Symptom:** Rockbox writes local wall-clock seconds into the timestamp column while hardcoding `#TZ/UTC` (or `#TZ/UNKNOWN`) in the header. If submitted naively, scrobbles are shifted by the host's timezone offset (e.g., 3 hours into the future for UTC-3), causing Last.fm to reject or misalign playback history.
- **Root Cause:** Multiple Rockbox DAP ports (notably modern Innioasis Y1 and Android port builds) lack an operational real-time clock (RTC) timezone translation layer and always emit static header strings.
- **Mitigation (`src/scrobbler/parser.py`):** `syncdap` ignores deceptive `#TZ/UTC` directives unless explicitly configured. It computes the host machine's active local UTC offset or reads `--timezone` / `scrobbler.tz_offset`:
  ```python
  # From src/scrobbler/parser.py
  if tz_directive == "UNKNOWN" or force_local_tz:
      local_offset = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
      adjusted_timestamp = raw_timestamp - local_offset
  ```

#### Quirk 2: Preservation of Consecutive Repeat Scrobbles
- **Symptom:** Third-party scrobblers drop repeated listens of the same track if consecutive timestamps fall within the track's duration.
- **Root Cause:** Flawed deduplication algorithms assuming repeated entries are write-buffer flush bugs.
- **Mitigation:** `syncdap` preserves every entry with `rating == "L"`. Dedup is strictly applied across synchronization sessions against a persistent watermark timestamp in `scrobbler.state`.

---

## Summary & Next Steps
Having examined how Rockbox parses tags and manages memory in RAM, let us inspect the second physical constraint: the underlying FAT32 storage volume and Virtual File System (VFS) boundaries.

---

> **The Syncdap Book Navigation:** [← Previous Section](../01-getting-started/02-configuration.md) • [Table of Contents](../index.md) • [Next Section →](02-fat32-storage.md)
