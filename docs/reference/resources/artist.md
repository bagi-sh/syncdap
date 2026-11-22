# Resource Reference: artist

The `artist` resource scopes operations to an artist folder or artist name within the library.

---

## 1. Syntax

```text
syncdap artist <action> <artist> [options]
```

Where `<artist>` can be either a relative/absolute directory path or the artist's name (which `syncdap` will resolve automatically within the target library root).

---

## 2. Actions

### `status`
Inspects total tracks, albums, format breakdown, and tag integrity for the specified artist.
```bash
syncdap artist status "Queen"
syncdap artist status ./Music/Queen
```

### `audit`
Scans the artist's tracks for playback duration anomalies and accidental full-album rips.
```bash
syncdap artist audit "Radiohead"
```

### `dedup`
Deduplicates audio files located within this artist's discography.
```bash
syncdap artist dedup "The Beatles" --dry-run
```

### `fix`
Standardizes `ALBUM` and `ALBUMARTIST` tags across all albums by this artist.
```bash
syncdap artist fix "Pink Floyd"
```

### `romaji`
Transliterates Japanese metadata and file paths for this artist into Hepburn Romaji.
```bash
syncdap artist romaji "Radwimps"
```

### `patch`
Transcodes or upgrades all tracks for this artist to the target format.
```bash
syncdap artist patch flac "Daft Punk"
```
