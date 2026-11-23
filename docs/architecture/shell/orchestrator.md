# Shell Coordinator: orchestrator.sh

`src/sh/orchestrator.sh` coordinates execution between shell-level arguments and the underlying Python processing modules, resolving directory paths, managing execution scopes, and chaining optimization pipelines.

---

## 1. Subcommand Execution Table

`orchestrator.sh` routes parsed commands to dedicated orchestration functions:

| Subcommand | Function | Python Module Invoked | Scope / Action |
|---|---|---|---|
| `download` | `orchestrate_download` | `src/sh/downloader.sh` | Spotify download via spotDL |
| `search` | `orchestrate_search` | `src/modules/search.py` | Query metadata via iTunes/MusicBrainz |
| `rescue` | `orchestrate_rescue` | `src/modules/fallback.py` | YouTube fallback download |
| `library` | `orchestrate_library` | Varies (`stats`, `audit`, `dedup`, etc.) | Library-wide maintenance |
| `artist` | `orchestrate_artist` | Varies | Scoped to `/Music/<Artist>/` |
| `album` | `orchestrate_album` | Varies (`album_expander.py`, etc.) | Scoped to `/Music/<Artist>/<Album>/` |
| `track` | `orchestrate_track` | `src/patch/worker.py`, etc. | Scoped to individual audio file |
| `playlist` | `orchestrate_playlist` | `src/playlists/cli.py` | Interactive M3U manager |
| `covers` | `orchestrate_covers` | `src/modules/covers.py` | Cover extraction & APIC stripping |
| `lyrics` | `orchestrate_lyrics` | `src/modules/lyrics.py` | LRCLIB synchronization |
| `tags` | `orchestrate_tags` | `src/modules/rockbox_tags.py` | Split-album tag unification |
| `scrobbler`| `orchestrate_scrobbler`| `src/scrobbler/cli.py` | Last.fm log sync |

---

## 2. Dynamic Target Path Resolution (`resolve_music_root`)

`syncdap` handles both flat folder structures and standard DAP structures (`/mnt/dap/Music/`):
```bash
# Excerpt from src/sh/common.sh & orchestrator.sh
resolve_music_root() {
    local base="${TARGET_ROOT:-.}"
    if [ -d "$base/Music" ]; then
        echo "$base/Music"
    else
        echo "$base"
    fi
}
```

When targeting an artist (`syncdap artist audit "Queen"`):
1. `orchestrator.sh` checks if `$music_root/Queen` exists.
2. If absent, it performs case-insensitive directory matching:
   ```bash
   find "$music_root" -maxdepth 1 -mindepth 1 -type d -iname "$target_artist"
   ```
3. If no matching folder is found, it reports an `error_dual` on `stderr` and exits with code 2.

---

## 3. Full Optimization Pipeline (`orchestrate_optimize`)

Executing `syncdap library optimize -r /mnt/dap` runs a coordinated multi-module pipeline:

```bash
# Logic structure from src/sh/orchestrator.sh
orchestrate_optimize() {
    local music_root
    music_root="$(resolve_music_root)"

    echo -e "${BLUE}${ICON_DISC} Step 1/4: Deduplicating audio tracks...${RESET}" >&2
    run_py "$SCRIPT_DIR/src/modules/dedup.py" -r "$music_root" $([ "$DRY_RUN" = true ] && echo "--dry-run")

    echo -e "${BLUE}${ICON_IMG} Step 2/4: Optimizing cover artwork (cover.jpg)...${RESET}" >&2
    run_py "$SCRIPT_DIR/src/modules/covers.py" optimize -r "$music_root" $([ "$DRY_RUN" = true ] && echo "--dry-run")

    echo -e "${BLUE}${ICON_TAG} Step 3/4: Unifying Rockbox ALBUMARTIST tags...${RESET}" >&2
    run_py "$SCRIPT_DIR/src/modules/rockbox_tags.py" fix -r "$music_root" $([ "$DRY_RUN" = true ] && echo "--dry-run")

    echo -e "${BLUE}${ICON_PL} Step 4/4: Relinking and repairing playlists...${RESET}" >&2
    run_py "$SCRIPT_DIR/src/modules/playlist_repair.py" -r "$TARGET_ROOT" $([ "$DRY_RUN" = true ] && echo "--dry-run")
}
```

Each stage inherits the global `-n` / `--dry-run` flag to preview modifications before touching disk files.
