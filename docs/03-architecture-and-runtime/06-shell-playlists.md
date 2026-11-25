# Chapter 3.6: Shell Playlist Synchronization & VFS Remapping (`playlists.sh`)

> **The Syncdap Book Navigation:** [← Previous Section](05-shell-downloader.md) • [Table of Contents](../index.md) • [Next Section →](07-shell-icons.md)

---

## Pedagogical Context & Prerequisites
This section inspects `playlists.sh`, the shell coordinator responsible for synchronizing local playlist files (`.m3u`, `.m3u8`) with the DAP's internal storage volume.

---

`src/sh/playlists.sh` coordinates post-download playlist relocation, relative path normalization, and UTF-8 encoding enforcement for Rockbox DAP environments.

---

## 1. Directory Structure & Path Invariants

Rockbox and DAP directory standards require playlists to be stored in a dedicated `Playlists/` directory at the same hierarchical level as the `Music/` directory (or directly inside the music root):

```text
/mnt/dap/
├── Music/
│   └── Artist/
│       └── Album/
│           └── 01 Track.mp3
└── Playlists/
    └── Favorites.m3u8
```

### Destination Discovery
```bash
# Excerpt from src/sh/playlists.sh
local pl_dir="../Playlists"
if ! mkdir -p "$pl_dir" 2>/dev/null; then
    pl_dir="Playlists"
    mkdir -p "$pl_dir" 2>/dev/null || true
fi
```
If executed inside `/mnt/dap/Music/`, `../Playlists` places the playlist into `/mnt/dap/Playlists/`. If permissions fail or running from a flat directory, it creates `./Playlists/`.

---

## 2. In-Memory Relative Path Translation

spotDL writes playlists containing absolute paths or paths relative to the current download working directory. `playlists.sh` embeds an inline Python processing script to sanitize every playlist line:

```python
# From src/sh/playlists.sh
import sys, os
path = sys.argv[1]
try:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    out = []
    has_header = False
    pl_dir = os.path.dirname(os.path.abspath(path))
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('#EXTM3U'):
            has_header = True
            out.append(s)
            continue
        if s.startswith('#'):
            out.append(s)
            continue
        # Convert path to relative from the playlist directory
        target = s
        if not os.path.isabs(target):
            target = os.path.abspath(os.path.join(os.getcwd(), target))
        if os.path.exists(target):
            rel = os.path.relpath(target, pl_dir)
            out.append(rel)
        else:
            out.append(s)
    
    with open(path, 'w', encoding='utf-8') as f:
        if not has_header:
            f.write('#EXTM3U\n')
        for l in out:
            f.write(l + '\n')
except Exception as e:
    pass
```

### Contract Guarantees
- **`#EXTM3U` Header Enforcement:** If missing, `#EXTM3U` is prepended to the top of the file.
- **Relative Path Calculation:** All audio targets are rewritten using `os.path.relpath(target, pl_dir)` (e.g. `../Music/Artist/Album/01 Track.mp3`). This ensures playlists remain valid across Linux host mounts (`/mnt/dap`) and Rockbox internal root mounts (`/`).
- **Encoding:** Output is saved strictly in **UTF-8 without BOM** and with `.m3u8` extension (`.m3u` files are automatically renamed to `.m3u8`).

---

## Summary & Next Steps
Next, we inspect terminal presentation and how `syncdap` detects terminal capabilities to render monochromatic Nerd Font glyphs.

---

> **The Syncdap Book Navigation:** [← Previous Section](05-shell-downloader.md) • [Table of Contents](../index.md) • [Next Section →](07-shell-icons.md)
