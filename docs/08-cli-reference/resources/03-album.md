# Chapter 8.3.3: Resource Command Reference: `syncdap album`

> **The Syncdap Book Navigation:** [← Previous Section](02-artist.md) • [Table of Contents](../../index.md) • [Next Section →](04-track.md)

---

## Pedagogical Context & Prerequisites
This section documents album-scoped commands: status, audit, dedup, expand, optimize, patch, fix, and romaji.

---

The `album` resource scopes operations to an album directory or unbundles single-file album rips.

---

## 1. Syntax

```text
syncdap album <action> [album_dir_or_file] [options]
```

---

## 2. Actions

### `status`
Inspects album track count, bitrates, cover art status, and tag completeness.
```bash
syncdap album status ./A_Night_at_the_Opera/
```

### `audit`
Checks whether tracks in the album exceed expected durations.
```bash
syncdap album audit ./Abbey_Road/
```

### `expand`
Unbundles a single-file full-album rip into individually tagged audio tracks.
```bash
syncdap album expand ./FullAlbumRip.mp3
syncdap album expand ./FullAlbumRip.flac -F flac
```

### `optimize`
Runs the Rockbox optimization pipeline strictly within the target album folder (extracts `cover.jpg`, strips embedded artwork, normalizes `ALBUMARTIST`, and cleans ghost files).
```bash
syncdap album optimize ./Dark_Side_of_the_Moon/
```

### `dedup`
Removes duplicate tracks within the album folder.
```bash
syncdap album dedup ./Discovery/
```

### `fix`
Unifies `ALBUM` and `ALBUMARTIST` for all tracks in the folder.
```bash
syncdap album fix ./Random_Access_Memories/
```

### `romaji`
Transliterates Japanese tags and filenames for this album.
```bash
syncdap album romaji ./Your_Name_OST/
```

### `patch`
Transcodes or upgrades the tracks in this album to the target format.
```bash
syncdap album patch flac ./A_Night_at_the_Opera/
```

---

## Summary & Next Steps
Next, we examine single-file operations with `syncdap track`.

---

> **The Syncdap Book Navigation:** [← Previous Section](02-artist.md) • [Table of Contents](../../index.md) • [Next Section →](04-track.md)
