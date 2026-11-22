# Shell Coordinator: orchestrator.sh

`src/sh/orchestrator.sh` delegates operations from CLI inputs to the appropriate internal Python engines and external downloaders.

---

## 1. Responsibilities

* **Entity Dispatch:** Routes execution across scopes (`orchestrate_library`, `orchestrate_artist`, `orchestrate_album`, `orchestrate_track`).
* **Target Resolution:** Resolves artist and album directory paths dynamically when names or relative paths are passed.
* **Full Optimization Pipeline (`orchestrate_optimize`):** Chaining deduplication, cover art extraction, tag unification, and playlist repair.
* **Execution Formatting:** Routes informative diagnostics to `stderr` (`>&2`) while preserving clean data on `stdout`.

---

## 2. Scoped Orchestration Functions

### `orchestrate_library`
Executes operations across the entire music collection or DAP mount:
* `status`: Calls `src/modules/stats.py -r "$music_root"`.
* `audit`: Scans for tracks >10m across the library using `src/modules/audit.py`.
* `dedup`: Deduplicates audio files across all albums.
* `optimize`: Runs the complete Rockbox pipeline.
* `fix`: Standardizes `ALBUM` and `ALBUMARTIST` across all folders.
* `romaji`: Transliterates Japanese text across the library.

### `orchestrate_artist`
Resolves the target artist folder within `$music_root` and scopes the operation:
```bash
syncdap artist status "Queen"
syncdap artist fix "Pink Floyd"
```

### `orchestrate_album`
Targets a specific album folder or rip file:
```bash
syncdap album audit ./Abbey_Road/
syncdap album expand ./FullRip.mp3
syncdap album optimize ./A_Night_at_the_Opera/
```

### `orchestrate_track`
Executes single-file inspection, expansion, transliteration, or transcoding:
```bash
syncdap track status ./Bohemian_Rhapsody.flac
syncdap track patch mp3 ./Lossless_Track.wav
```
