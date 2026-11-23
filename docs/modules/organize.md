# Python Module: organize.py

`src/modules/organize.py` scans a music collection or Digital Audio Player (DAP) storage volume and restructures all audio files and associated sidecars into syncdap's canonical Rockbox folder and filename hierarchy.

```text
Input (Arbitrary / Disorganized):
/mnt/dap/
├── Downloads/
│   └── 01 - Song Name.mp3
└── Unsorted/
    ├── artist_track.flac
    ├── artist_track.lrc
    └── folder.jpg

Canonical Output (syncdap / Rockbox Structure):
/mnt/dap/Music/
└── {AlbumArtist}/
    └── {Album}/
        ├── cover.jpg
        ├── 01 Song Name - Artist.mp3
        ├── 02 Track Title - Artist.flac
        └── 02 Track Title - Artist.lrc
```

---

## 1. Metadata Extraction & Canonical Path Resolution

The module determines the destination directory and filename for each audio file using `compute_canonical_destination()`:

```python
# From src/modules/organize.py
def compute_canonical_destination(
    file_path: str,
    music_root: str,
) -> tuple[str, str, dict]:
```

### Tag Precedence Resolution
To ensure multi-artist albums and compilations remain grouped together under a single album folder rather than splintering across individual artist folders, tags are evaluated in the following priority order:

1. **Folder Artist (`artist_folder`):**
   $$\text{Tag Priority: } \text{raw\_meta}[\text{"album\_artist"}] \;\to\; \text{raw\_meta}[\text{"artist"}] \;\to\; \text{fn\_meta}[\text{"artist"}] \;\to\; \text{"Unknown Artist"}$$
2. **Track Artist (`track_artist`):**
   $$\text{Tag Priority: } \text{raw\_meta}[\text{"artist"}] \;\to\; \text{raw\_meta}[\text{"album\_artist"}] \;\to\; \text{fn\_meta}[\text{"artist"}] \;\to\; \text{artist\_folder}$$
3. **Album Name (`album_folder`):**
   $$\text{Tag Priority: } \text{raw\_meta}[\text{"album"}] \;\to\; \text{fn\_meta}[\text{"album"}] \;\to\; \text{"Unknown Album"}$$
4. **Track Title (`title`):**
   $$\text{Tag Priority: } \text{raw\_meta}[\text{"title"}] \;\to\; \text{fn\_meta}[\text{"title"}] \;\to\; \text{basename without extension}$$
5. **Track Number Prefix (`track_prefix`):**
   - Parsed integer from `raw_meta["track_num"]` (supporting `"03/12"` notation) or `fn_meta["track_no"]`.
   - Formatted as 2-digit zero-padded prefix: `f"{track_num:02d} "` (e.g. `"01 "`). If zero or missing, the prefix is omitted.

### FAT32 / exFAT Filename Sanitization
All path components (`safe_artist_folder`, `safe_album_folder`, `safe_title`, `safe_track_artist`) are sanitized using `share.sanitize_filename()`:
- Illegal characters on FAT32/VFS (`/ \ : * ? " < > |`) are stripped or replaced with underscores.
- Leading and trailing periods and whitespace are trimmed to avoid VFS truncation bugs.
- Destination template:
  $$\text{Target File} = \text{music\_root} \,/\, \text{safe\_artist} \,/\, \text{safe\_album} \,/\, \left(\text{track\_prefix} + \text{safe\_title} + \text{" - "} + \text{safe\_track\_artist} + \text{ext}\right)$$

---

## 2. Sidecar & Artwork Lifecycle

Audio files rarely exist in isolation. `organize.py` manages all associated sidecars during relocation:

### Synchronized Lyrics (`.lrc`)
When an audio file `song.ext` is moved, `organize.py` checks for a sibling file with the same stem and `.lrc` extension (`song.lrc`). If present and non-empty:
- The `.lrc` file is relocated alongside the audio file to `{dest_dir}/{canonical_filename}.lrc`.
- Character encoding is preserved intact.

### Album Artwork (`cover.jpg`)
For each audio track moved, the source directory is inspected for candidate artwork matching `COVER_FILENAMES` (`cover.jpg`, `folder.jpg`, `album.jpg`, `front.jpg`).
- If candidate artwork exists and the target album folder does not yet contain an image, the file is migrated and normalized to `{dest_dir}/cover.jpg`.
- Prevents redundant duplicate copies when multiple tracks from the same album are moved.

---

## 3. Two-Phase Execution & Collision Protection

To prevent partial moves, catastrophic data loss, or race conditions on FAT32 volumes, reorganization runs in two distinct phases:

```text
┌─────────────────────────┐
│ Phase 1: Planning       │  Scan library, extract tags, compute destinations,
│ plan_library_organize() │  detect collisions, identify sidecars and artwork.
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Confirmation Prompt     │  Prompt user with item counts ([y/N]),
│ (Skipped if -n or -y)   │  or emit machine JSON if --json is passed.
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Phase 2: Execution      │  Execute atomic shutil.move, migrate sidecars,
│ execute_library_org()   │  relink playlists, prune empty directories.
└─────────────────────────┘
```

### Collision Resolution
If two distinct source tracks resolve to the identical canonical destination (e.g. duplicate files or multiple tracks with missing metadata), destination claiming automatically resolves collisions:
```python
final_dest = dest_path
counter = 1
stem, ext = os.path.splitext(dest_path)
while final_dest in claimed_destinations or (os.path.exists(final_dest) and os.path.abspath(final_dest) != src_path):
    final_dest = f"{stem} ({counter}){ext}"
    counter += 1
```

### Playlist Relinking
Whenever files are physically moved, an in-memory translation map (`path_map[src] = dest`) is passed to `share.update_all_playlists()`. Every M3U/M3U8 file within the target volume is scanned and updated with the new relative or absolute paths.

---

## 4. JSON Schema & Dual-Audience Telemetry

When `--json` is supplied, `organize.py` suppresses interactive terminal output and emits structured metrics to `stdout`:

```json
{
  "music_root": "/mnt/dap/Music",
  "total_tracks": 142,
  "already_organized": 120,
  "dry_run": false,
  "audio_moved": 22,
  "lrc_moved": 18,
  "covers_migrated": 2,
  "playlists_updated": 3
}
```

Interactive execution displays clear progress indicators via `stderr`:
```text
󰎈 Scanning library to plan organization at: /mnt/dap
   Canonical destination root:  /mnt/dap/Music
   Total audio tracks found:     142
   Already in canonical layout:  120
   Tracks requiring movement:    22

󰎈 Reorganizing 22 track(s)...
   󰁔 Moving: Unsorted/track.mp3 -> Music/Artist/Album/01 Title - Artist.mp3
      󰄬 Moved sidecar lyrics: 01 Title - Artist.lrc
      󰥠 Migrated album cover to: Music/Artist/Album/cover.jpg

󰄬 Successfully organized library:
   - Audio tracks moved:     22
   - Lyrics (.lrc) moved:    18
   - Album covers migrated:  2
   - Playlists relinked:     3
```

---

## 5. CLI Invocation Reference

```bash
# Preview reorganization plan without touching files on disk
syncdap library organize --dry-run

# Run reorganization on current directory with interactive prompt
syncdap library organize

# Non-interactive reorganization directly on connected DAP mount
syncdap library organize -r /mnt/dap -y -v

# Emit machine-readable summary
syncdap library organize -r /mnt/dap --json
```
