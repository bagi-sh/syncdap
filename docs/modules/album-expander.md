# Python Module: album_expander.py

`src/modules/album_expander.py` handles unbundling full-album single-file rips into properly split, individually tagged tracks by re-downloading or stream-splitting.

---

## 1. Capabilities

* **Metadata Extraction:** Extracts artist, album, and release information from the single-file rip.
* **Tracklist Resolution:** Resolves the canonical album tracklist via iTunes or MusicBrainz.
* **Safe Replacement:** Downloads individual tracks, verifies audio integrity, removes the obsolete single-file rip, and updates playlist references.
* **Simulation Mode:** Supports `--dry-run` to inspect proposed unbundling without touching disk files.

---

## 2. CLI Usage

```bash
# Expand all detected rips in library
python3 src/modules/album_expander.py -r /path/to/music

# Expand a specific single-file rip
python3 src/modules/album_expander.py -r /path/to/music "/path/to/music/Artist/Album/full_album.mp3"

# Dry-run preview
python3 src/modules/album_expander.py -r /path/to/music --dry-run
```
