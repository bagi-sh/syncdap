# Python Module: playlists Subsystem (`src/playlists/`)

`src/playlists/` provides an interactive terminal manager and automation engine for manipulating, merging, deduplicating, and auditing M3U/M3U8 playlists.

---

## 1. Subsystem Architecture

- `core.py`: Parser and serializer for M3U and extended `#EXTINF` metadata records.
- `manager.py`: Full-screen or interactive menu system displaying track counts, disk usage, and missing files.
- `actions.py`: Non-interactive CLI flows for merging playlists and deleting playlists with safety confirmations.
- `ui.py`: Formatted terminal tables and status cards.

---

## 2. Playlist Merging & Deduplication

When merging multiple playlists (`syncdap playlist merge <pl1> <pl2> [out_name]`):
1. **Track De-duplication:** Tracks are deduplicated based on resolved canonical file paths, preserving the original ordering of unique entries.
2. **Relative Path Recalculation:** All audio paths in the merged output are computed relative to the destination playlist file.
3. **Source Deletion (`--delete-sources`):** Optional flag to delete the original source playlists after a successful merge.

```python
# Logic from src/playlists/actions.py
def merge_playlists_flow(pl1_name, pl2_name, out_name=None, delete_sources=False, assume_yes=False):
    # Resolves paths, parses tracks, merges unique items, and saves output UTF-8
```

---

## 3. Storage & Health Dashboard

When launching `syncdap playlist manage`, the manager calculates aggregate metrics across all playlists:
- Total playlists discovered.
- Cumulative audio playtime and storage footprint.
- Broken / missing file references.
- Cross-playlist shared track overlap percentages.

---

## 4. CLI Invocations

```bash
# Launch interactive terminal manager
syncdap playlist manage

# Merge two playlists into a new consolidated list
syncdap playlist merge "Driving" "Roadtrip" "Ultimate_Roadtrip"

# Delete a playlist with confirmation bypass
syncdap playlist delete "Obsolete" -y
```
