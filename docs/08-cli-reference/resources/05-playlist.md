# Chapter 8.3.5: Resource Command Reference: `syncdap playlist`

> **The Syncdap Book Navigation:** [← Previous Section](04-track.md) • [Table of Contents](../../index.md) • [Next Section →](06-covers.md)

---

## Pedagogical Context & Prerequisites
This section documents playlist management actions: manage, merge, delete, and repair.

---

The `playlist` resource manages, repairs, and merges `.m3u` and `.m3u8` playlists.

---

## 1. Syntax

```text
syncdap playlist <action> [arguments] [options]
```

---

## 2. Actions

### `manage`
Launches the interactive terminal playlist manager.
```bash
syncdap playlist manage
syncdap playlist manage "Favorites"
```

### `merge`
Merges two playlists and deduplicates shared tracks.
```bash
syncdap playlist merge ListA.m3u8 ListB.m3u8 Merged.m3u8
```

### `delete`
Deletes a playlist file and optionally prompts to purge unshared audio files.
```bash
syncdap playlist delete "OldPlaylist.m3u8"
syncdap playlist delete "OldPlaylist.m3u8" --yes
```

### `repair`
Audits all playlists in the library, relinking moved or renamed files and pruning dead links.
```bash
syncdap playlist repair
syncdap playlist repair --dry-run
```

---

## Summary & Next Steps
Next, we examine artwork actions with `syncdap covers`.

---

> **The Syncdap Book Navigation:** [← Previous Section](04-track.md) • [Table of Contents](../../index.md) • [Next Section →](06-covers.md)
