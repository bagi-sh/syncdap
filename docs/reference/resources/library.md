# Resource Reference: library

The `library` resource coordinates library-wide operations across your entire collection or DAP mount.

---

## 1. Syntax

```text
syncdap library <action> [options]
```

---

## 2. Actions

### `status`
Displays library health, storage allocation, audio format distribution, lyrics coverage, and Rockbox split-album tag audit.
```bash
# Standard table view
syncdap library status

# Machine-readable JSON
syncdap library status --json

# Target DAP mount directly
syncdap library status -r /mnt/dap/Music
```

### `audit`
Scans all audio files across the library to detect tracks longer than 10 minutes whose durations exceed official API releases by >1.5x (accidental full-album rips).
```bash
syncdap library audit
syncdap library audit --json
```

### `dedup`
Identifies duplicate tracks across albums, keeps the highest audio quality copy (prioritizing lossless FLAC over MP3), and relinks all playlists.
```bash
syncdap library dedup
syncdap library dedup --dry-run
```

### `optimize`
Executes the complete Rockbox optimization pipeline: deduplication, external `cover.jpg` extraction, embedded artwork tag stripping, `ALBUMARTIST` normalization, and playlist repair.
```bash
syncdap library optimize
syncdap library optimize -n
```

### `patch`
Transcodes or upgrades the entire library to a target audio container.
```bash
# Upgrade/transcode library to FLAC
syncdap library patch flac

# Transcode to 320kbps MP3
syncdap library patch mp3
```

### `fix`
Standardizes `ALBUM` and `ALBUMARTIST` tags across every folder in the library to eliminate split albums in Rockbox, and deletes zero-byte ghost files.
```bash
syncdap library fix
syncdap library fix -n
```

### `organize`
Restructures and standardizes audio files from any arbitrary or disorganized layout into syncdap's canonical Rockbox hierarchy:
`Music/{AlbumArtist}/{Album}/{track_num} {title} - {track_artist}.ext`
Also moves matching synchronized lyrics (`.lrc`), migrates folder artwork (`cover.jpg`), updates playlist paths, and prunes orphaned empty directories.
```bash
# Preview reorganization plan without moving files
syncdap library organize --dry-run

# Reorganize library with interactive confirmation
syncdap library organize

# Non-interactive reorganization directly on DAP
syncdap library organize -r /mnt/dap -y -v
```

### `romaji`
Transliterates Japanese Kanji, Hiragana, and Katakana across all tags, filenames, and `.lrc` files in the library to Hepburn Romaji.
```bash
syncdap library romaji
syncdap library romaji -n
```
