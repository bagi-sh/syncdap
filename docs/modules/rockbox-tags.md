# Python Module: rockbox_tags.py

`src/modules/rockbox_tags.py` standardizes metadata tags across album directories to prevent Rockbox from splitting albums, while cleaning zero-byte ghost files.

---

## 1. Capabilities

* **Split Album Prevention:** Inspects all tracks within an album directory and enforces an identical, canonical `ALBUMARTIST` and `ALBUM` tag across every file.
* **Ghost File Cleanup:** Detects and deletes 0-byte corrupt audio files and orphaned `.dot` files (such as macOS `._*` resource fork files).
* **ID3v2.3 Compliance:** Writes UTF-16 ID3v2.3 tags for maximum compatibility with older DAP hardware.
* **Simulation Mode:** Supports `--dry-run` to preview tag changes without modifying files.

---

## 2. CLI Usage

```bash
# Standardize tags and fix split albums across library
python3 src/modules/rockbox_tags.py -r /path/to/music

# Dry-run preview
python3 src/modules/rockbox_tags.py -r /path/to/music --dry-run
```
