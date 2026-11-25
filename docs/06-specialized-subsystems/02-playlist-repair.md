# Chapter 6.2: Fuzzy Levenshtein Playlist Relinking (`playlist_repair.py`)

> **The Syncdap Book Navigation:** [← Previous Section](01-playlists.md) • [Table of Contents](../index.md) • [Next Section →](03-romaji.md)

---

## Pedagogical Context & Prerequisites
In this section, we analyze `playlist_repair.py`, which scans playlist files, detects dead or relocated target tracks, and restores broken references using fuzzy Levenshtein string matching.

---

`src/modules/playlist_repair.py` repairs broken, relocated, or reformatted playlist paths, relinking missing tracks to their canonical files using in-memory path indexes and normalized stem matching.

---

## 1. The In-Memory Lookup Index

When auditing playlists, naive filesystem traversal for every missing track causes significant disk I/O lag on slow USB/FAT32 connections. `playlist_repair.py` builds an in-memory index in a single pass:

```python
# From src/modules/playlist_repair.py
def build_library_index(music_dir):
    music_dir = os.path.abspath(music_dir)
    folder_map = {}
    by_norm_stem = defaultdict(list)
    by_norm_fn = defaultdict(list)

    for root, dirs, files in os.walk(music_dir):
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS and not d.startswith('.Trash')]
        rel = os.path.relpath(root, music_dir)
        parts = rel.split(os.sep)
        if len(parts) >= 2:
            key = (norm_str(parts[0]), norm_str(parts[1]))
            folder_map[key] = root

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                full_path = os.path.join(root, f)
                stem = os.path.splitext(f)[0]
                by_norm_stem[norm_str(stem)].append(full_path)
                by_norm_fn[norm_str(f)].append(full_path)
```

---

## 2. Multi-Stage Resolution Protocol

When a playlist references a file that does not exist at its specified location:
1. **Direct Path Check:** Checks if the file exists relative to the playlist file's directory.
2. **Normalized Stem Match (`by_norm_stem`):** If a track was transcoded from `.mp3` to `.flac`, the stem matches, and the path is rewritten to the new extension.
3. **Folder & Title Match (`folder_map`):** If artist or album directories were renamed or cleaned, the normalized `(artist, album)` tuple locates the relocated folder.
4. **Dead Link Pruning:** If a referenced track cannot be resolved anywhere in the library index, the entry is pruned to prevent Rockbox playback errors.

---

## 3. Formatting & Relative Path Rewriting

Playlists are rewritten in **UTF-8 without BOM**:
- Every audio path is converted to a clean relative path from the playlist file's folder (e.g. `../Music/Artist/Album/01 Track.flac`).
- Trailing spaces and Windows CRLF (`\r\n`) line endings are normalized to Unix LF (`\n`).

---

## 4. CLI Invocations

```bash
# Repair all playlists in default Playlists directory
syncdap playlist repair -r /mnt/dap

# Repair a specific playlist file
python3 src/modules/playlist_repair.py -r /mnt/dap/Music /mnt/dap/Playlists/Rock.m3u8

# Preview repairs without rewriting files
syncdap playlist repair -r /mnt/dap --dry-run
```

---

## Summary & Next Steps
Next, we examine `src/romaji/`, which solves DAP non-Latin character display limitations through Japanese Romaji transliteration.

---

> **The Syncdap Book Navigation:** [← Previous Section](01-playlists.md) • [Table of Contents](../index.md) • [Next Section →](03-romaji.md)
