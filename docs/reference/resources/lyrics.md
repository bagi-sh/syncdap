# Resource Reference: lyrics

The `lyrics` resource manages timestamped `.lrc` lyrics search, retrieval, and metadata embedding.

---

## 1. Syntax

```text
syncdap lyrics <action> [options]
```

---

## 2. Actions

### `fetch`
Scans album folders for tracks missing `.lrc` files and downloads timestamped lyrics from LRCLIB and `syncedlyrics`.
```bash
# Fetch missing lyrics
syncdap lyrics fetch

# Fetch strictly timestamped [mm:ss] synchronized lyrics
syncdap lyrics fetch --synced-only
```

### `embed`
Embeds `.lrc` lyrics directly into audio metadata tags (`USLT`/`SYLT` for ID3; `LYRICS` Vorbis comment).
```bash
syncdap lyrics embed
```
