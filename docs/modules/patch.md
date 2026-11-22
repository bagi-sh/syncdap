# Python Subsystem: patch

The `src/patch/` subsystem manages audio format transcoding, quality upgrades, and batch conversion.

---

## 1. Package Structure

* `src/patch/cli.py` – Subsystem argument parser and execution dispatcher.
* `src/patch/worker.py` – Worker thread pool managing stream re-downloads and ffmpeg transcoding.
* `src/patch/metadata.py` – Metadata preservation across transcoded audio containers.
* `src/patch/playlist.py` – Playlist relinking after format changes (e.g., updating `.mp3` to `.flac`).

---

## 2. Supported Formats

Supports bidirectional transcoding and stream upgrading across:
* **`flac`** (Lossless Free Lossless Audio Codec)
* **`mp3`** (MPEG Layer-3, default 320kbps)
* **`m4a`** (AAC Advanced Audio Coding)
* **`opus`** (High-efficiency Ogg Opus)
* **`ogg`** (Ogg Vorbis)
* **`wav`** (Uncompressed linear PCM)

---

## 3. CLI Usage

```bash
# Upgrade target folder to FLAC
python3 src/patch/cli.py flac /tmp/session 4 false false "/path/to/album" "" false
```
