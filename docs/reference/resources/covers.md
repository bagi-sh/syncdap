# Resource Reference: covers

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
