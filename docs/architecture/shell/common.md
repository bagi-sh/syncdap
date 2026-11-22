# Shell Coordinator: common.sh

`src/sh/common.sh` provides the shared runtime foundation, process traps, dependency checks, and Python execution wrappers for all shell scripts.

---

## 1. Environment & Temporary Directories

To prevent orphaned files or unauthorized root filesystem writes, `common.sh` establishes an isolated session directory:
```bash
setup_environment() {
    [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ] && return 0
    MARKER=$(mktemp -t syncdap_marker.XXXXXX 2>/dev/null || mktemp /tmp/syncdap_marker.XXXXXX)
    TEMP_DIR=$(mktemp -d -t syncdap_session.XXXXXX 2>/dev/null || mktemp -d /tmp/syncdap_session.XXXXXX)
    trap cleanup EXIT INT TERM
    touch "$MARKER"
}
```

Upon termination (normal exit or interrupt), the `cleanup` trap automatically purges `$TEMP_DIR` and any temporary marker files.

---

## 2. Python Engine Execution (`run_py`)

`syncdap` executes Python modules through the `run_py` helper:
* Checks if **`uv`** is available on the system.
* Runs with isolated, pre-cached dependencies:
  ```bash
  uv run --offline --with mutagen,eyed3,requests,pykakasi python3 "$@"
  ```
* Seamlessly falls back to system `python3` if `uv` is absent.

---

## 3. Dependency Validation (`check_dependencies`)

Validates the presence of required system binaries: `ffmpeg`, `yt-dlp`, `python3`, `curl`, `grep`, and `spotDL`/`uv`. Missing tools result in immediate Dual-Audience error formatting on `stderr`.
