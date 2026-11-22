# Shell Coordinator: playlists.sh

`src/sh/playlists.sh` manages playlist normalization, path conversion, and Rockbox playlist directory synchronization.

---

## 1. Responsibilities

* **Path Normalization:** Converts absolute local filesystem paths into relative or Rockbox-compatible paths (`/Music/...`).
* **Playlist Relinking:** Moves newly downloaded `.m3u` or `.m3u8` playlists into the target `Playlists/` directory.
* **Dead Path Scrubbing:** Ensures files removed or upgraded during format patching are reflected accurately in playlist indices.
