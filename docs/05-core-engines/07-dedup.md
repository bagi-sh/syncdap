# Chapter 5.7: Lossless-Prioritizing Deduplication (`dedup.py`)

> **The Syncdap Book Navigation:** [← Previous Section](06-patch.md) • [Table of Contents](../index.md) • [Next Section →](08-fallback.md)

---

## Pedagogical Context & Prerequisites
Here, we examine `dedup.py`, which calculates audio fingerprints and quality tiers (FLAC > Opus > MP3 320k) to purge lower-quality duplicates and update playlist references.

---

`src/modules/dedup.py` identifies duplicated audio tracks across an album or library, evaluates quality metrics to determine the optimal file, purges inferior duplicates, and safely relinks playlists.

---

## 1. Duplicate Grouping Logic

Tracks are grouped into duplicate sets using two complementary keys:
1. **Primary Grouping (Same Directory + Stem):**
   Matches files in the same folder that share the same filename stem under different extensions (e.g. `01 Track.flac` and `01 Track.mp3`).
2. **Secondary Grouping (Same Directory + Track Number + Normalized Title):**
   Matches tracks in the same directory sharing the same track index and normalized title string (`normalize_str`), catching naming discrepancies such as `01. Bohemian Rhapsody.mp3` vs `01 - Bohemian Rhapsody.flac`.

```python
# From src/modules/dedup.py
def group_duplicates(audio_files):
    stem_groups = defaultdict(list)
    track_title_groups = defaultdict(list)

    for p in audio_files:
        info = extract_track_info(p)
        parent = info['parent_dir']
        norm_stem = normalize_str(info['stem'])
        stem_groups[(parent, norm_stem)].append(p)
```

---

## 2. Quality Scoring Algorithm

When choosing the "winner" among duplicates, `dedup.py` scores candidates based on codec and bitrate:

```python
# Scoring hierarchy from src/share/audio.py
def get_audio_quality_score(file_path: str) -> tuple[int, int]:
    ext = os.path.splitext(file_path)[1].lower()
    meta = get_audio_metadata(file_path)
    bitrate = meta.get('bitrate') or 0

    # Tier 1: Lossless formats (FLAC, WAV, ALAC, APE)
    if ext in LOSSLESS_EXTENSIONS:
        return (1000, bitrate)

    # Tier 2: Modern Lossy (Opus, M4A / AAC)
    if ext in ('.opus', '.m4a'):
        return (500, bitrate)

    # Tier 3: Legacy Lossy (MP3, OGG)
    if ext in ('.mp3', '.ogg'):
        return (100, bitrate)

    return (0, bitrate)
```

---

## 3. Sidecar & Playlist Relinking Guarantees

1. **LRC Preservation:** If the lower quality file possesses a companion `.lrc` lyrics file and the winning track lacks one, `dedup.py` copies the `.lrc` file to match the winner's filename before purging.
2. **Playlist Relinking:** Before deleting any duplicate, `update_all_playlists()` traverses all `.m3u` / `.m3u8` files in the library, replacing references to the discarded track with the canonical winner's path.
3. **Flash Safety:** File removal is guarded by `os.path.isfile()` verification of the winning file.

---

## Summary & Next Steps
When a download fails or a track is corrupted, `fallback.py` executes secondary stream rescue. Let us examine its architecture.

---

> **The Syncdap Book Navigation:** [← Previous Section](06-patch.md) • [Table of Contents](../index.md) • [Next Section →](08-fallback.md)
