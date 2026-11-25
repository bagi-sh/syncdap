# Chapter 8.3.7: Resource Command Reference: `syncdap lyrics`

> **The Syncdap Book Navigation:** [← Previous Section](06-covers.md) • [Table of Contents](../../index.md) • [Next Section →](08-tags.md)

---

## Pedagogical Context & Prerequisites
This section documents lyric operations: fetch and embed.

---

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

---

## Summary & Next Steps
Next, we examine audio tag standardization with `syncdap tags`.

---

> **The Syncdap Book Navigation:** [← Previous Section](06-covers.md) • [Table of Contents](../../index.md) • [Next Section →](08-tags.md)
