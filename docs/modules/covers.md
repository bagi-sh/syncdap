# Python Module: covers.py

`src/modules/covers.py` optimizes album artwork for Rockbox hardware constraints and provides universal cover embedding into MP3, FLAC, and M4A audio containers.

---

## 1. The Two Operational Modes

### Mode A: `optimize` (Rockbox DAP RAM Protection)
- **Goal:** Minimize DAP RAM consumption and disk waste.
- **Mechanism:**
  1. Searches the album folder for existing artwork (`cover.jpg`, `folder.jpg`).
  2. If missing, extracts the highest resolution embedded `APIC` frame from an audio file to disk as `/Music/<Artist>/<Album>/cover.jpg`.
  3. Strips embedded `APIC` frames from all audio tracks in that folder (`strip_covers_from_file()`).
- **Result:** Saves 1–5 MB of tag overhead per track, prevents out-of-memory crashes on 32 MB iPods, and speeds up Rockbox database indexing.

### Mode B: `embed` (Universal Standalone Portability)
- **Goal:** Embed artwork into file tags for modern car head units, smartphones, or players that do not support external `cover.jpg` sidecars.
- **Mechanism:**
  1. Locates `cover.jpg` (or extracts from one track).
  2. Embeds the JPEG bytes into ID3v2 `APIC` (MP3), `Picture` blocks (FLAC), or `covr` atoms (M4A).

---

## 2. Format-Specific Tag Mechanics

```python
# From src/share/covers.py
def embed_cover_in_file(file_path: str, img_data: bytes, mime_type: str = 'image/jpeg') -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.mp3':
        audio = MP3(file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        # Add APIC front cover (type 3)
        audio.tags.setall('APIC', [
            APIC(encoding=3, mime=mime_type, type=3, desc='Front Cover', data=img_data)
        ])
        audio.save(v2_version=3)
        return True
    elif ext == '.flac':
        audio = FLAC(file_path)
        pic = Picture()
        pic.data = img_data
        pic.type = 3
        pic.mime = mime_type
        audio.clear_pictures()
        audio.add_picture(pic)
        audio.save()
        return True
```

---

## 3. CLI Invocations

```bash
# Optimize artwork across entire DAP mount (extract cover.jpg and strip embedded tags)
syncdap covers optimize -r /mnt/dap/Music

# Embed cover.jpg into all tracks for an artist
syncdap covers embed -r /mnt/dap/Music/Queen

# Non-destructive dry-run
syncdap covers optimize -r /mnt/dap/Music --dry-run
```
