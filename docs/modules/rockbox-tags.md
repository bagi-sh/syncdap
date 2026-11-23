# Python Module: rockbox_tags.py

`src/modules/rockbox_tags.py` prevents split albums in Rockbox databases, standardizes inconsistent `ALBUM` and `ALBUMARTIST` tags, removes OS ghost files, and enforces ID3v2.3 compliance.

---

## 1. The Split Album Defect & Resolution

### Root Cause
Rockbox builds its internal database by grouping files with identical `ALBUM` strings. When compilation or collaboration albums have varying `ARTIST` frames and lack an identical `ALBUMARTIST` frame, Rockbox displays multiple disjointed copies of the album in the browser.

### Majority Tag Resolution
`rockbox_tags.py` audits every folder independently:
1. Collects all `ARTIST` and `ALBUMARTIST` tags across tracks in the directory.
2. If `ALBUMARTIST` is missing, it determines the canonical album artist via:
   - Matching parent directory name (`/Music/<Artist>/<Album>/`).
   - Statistical majority vote across track artists.
3. Rewrites `ALBUMARTIST` across 100% of the tracks in that directory.

```python
# From src/modules/rockbox_tags.py
def normalize_folder_tags(album_dir, dry_run=False):
    # Determines canonical albumartist and writes identical tags across files
```

---

## 2. Ghost File & Artifact Purging

Operating systems often litter FAT32/exFAT volumes with hidden metadata files that Rockbox mistakenly attempts to parse as audio tracks:
- **macOS Resource Forks:** `._*` files (AppleDouble headers).
- **Windows Thumbnail Caches:** `Thumbs.db`, `desktop.ini`, `ehthumbs.db`.
- **Desktop Artifacts:** `.DS_Store`.

When `syncdap tags fix` or `syncdap library optimize` is invoked, `rockbox_tags.py` purges these files automatically.

---

## 3. ID3v2.3 & UTF-16 Normalization

Rockbox has documented instability when reading ID3v2.4 UTF-8 tags on certain hardware revisions. `rockbox_tags.py` forces:
- **Specification:** ID3v2.3 (`v2_version=3`).
- **Text Encoding:** UTF-16 with BOM (`encoding=1`).
- Preserves track numbers, release dates (`TDRC`), titles, and genres.

---

## 4. CLI Invocations

```bash
# Fix split albums and clean ghost files across library
syncdap tags fix -r /mnt/dap/Music

# Fix a specific album folder
python3 src/modules/rockbox_tags.py fix "/mnt/dap/Music/David Bowie/Heroes"

# Preview tag changes without modifying files
syncdap tags fix -r /mnt/dap/Music --dry-run
```
