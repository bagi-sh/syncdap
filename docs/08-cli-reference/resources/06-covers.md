# Chapter 8.3.6: Resource Command Reference: `syncdap covers`

> **The Syncdap Book Navigation:** [← Previous Section](05-playlist.md) • [Table of Contents](../../index.md) • [Next Section →](07-lyrics.md)

---

## Pedagogical Context & Prerequisites
This section documents cover artwork maintenance: optimize and embed.

---

The `covers` resource manages album artwork extraction and tag embedding.

---

## 1. Syntax

```text
syncdap covers <action> [options]
```

---

## 2. Actions

### `optimize`
Extracts embedded image frames to a directory-level `cover.jpg` file and strips embedded artwork from audio files. This is the optimal configuration for Rockbox and portable DAPs, minimizing RAM usage during playback.
```bash
syncdap covers optimize
syncdap covers optimize -r /mnt/dap/Music
```

### `embed`
Embeds the local `cover.jpg` file from each album directory directly into the audio metadata tags (`APIC` frame for MP3, `METADATA_BLOCK_PICTURE` for FLAC).
```bash
syncdap covers embed
```

---

## Summary & Next Steps
Next, we examine synchronized lyric commands with `syncdap lyrics`.

---

> **The Syncdap Book Navigation:** [← Previous Section](05-playlist.md) • [Table of Contents](../../index.md) • [Next Section →](07-lyrics.md)
