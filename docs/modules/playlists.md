# Python Subsystem: playlists

The `src/playlists/` package provides interactive terminal management, merging, deduplication, and maintenance for `.m3u` and `.m3u8` playlists.

---

## 1. Package Structure

* `src/playlists/cli.py` – Command-line interface and argument router.
* `src/playlists/actions.py` – Core operations: merging playlists, deleting playlists, and purging orphaned audio files.
* `src/playlists/manager.py` – Interactive terminal UI engine for inspecting and modifying playlist tracks.
* `src/playlists/core.py` – Playlist file I/O and entry parsing.
* `src/playlists/ui.py` – Text styling and table formatting for terminal displays.

---

## 2. Invocations

```bash
# Launch interactive terminal playlist manager
python3 src/playlists/cli.py --menu

# Merge two playlists and remove duplicate tracks
python3 src/playlists/cli.py --merge PlaylistA.m3u8 PlaylistB.m3u8 Merged.m3u8

# Delete a playlist file
python3 src/playlists/cli.py --delete OldList.m3u8 --yes
```
