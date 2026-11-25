# Chapter 3.4: Runtime Lifecycle, Signal Traps & Temp Directories (`common.sh`)

> **The Syncdap Book Navigation:** [← Previous Section](03-shell-orchestrator.md) • [Table of Contents](../index.md) • [Next Section →](05-shell-downloader.md)

---

## Pedagogical Context & Prerequisites
Long-running audio operations must never leave corrupt state when interrupted. In this section, we study how `common.sh` registers POSIX signal traps (`trap cleanup EXIT INT TERM`) and provides safe Python execution wrappers.

---

`src/sh/common.sh` establishes the shared execution foundation for all `syncdap` shell modules, providing process traps, isolated runtime environments, dependency verification, and Python runner wrappers.

---

## 1. Runtime State & Defaults

Upon sourcing, `common.sh` sets shell safety flags:
```bash
set -uo pipefail
```
It initializes global state variables and loads user configuration overrides:

```bash
SYNCDAP_VERSION="1.0.0"

# Defaults prior to config/flag override
AUDIO_FORMAT="mp3"
THREADS=4
SYNCED_ONLY=false
ASSUME_YES=false
KEEP_OLD=false
DRY_RUN=false
VERBOSE=false
QUIET=false
TARGET_ROOT="."
FORCE_ICONS="auto"
```

---

## 2. Process Isolation & Temporary Directory Traps

To ensure complete crash safety and avoid leaving leftover temporary files during failed downloads or interrupted operations:

```bash
# Excerpt from src/sh/common.sh
setup_environment() {
    [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ] && return 0
    MARKER=$(mktemp -t syncdap_marker.XXXXXX 2>/dev/null || mktemp /tmp/syncdap_marker.XXXXXX)
    TEMP_DIR=$(mktemp -d -t syncdap_session.XXXXXX 2>/dev/null || mktemp -d /tmp/syncdap_session.XXXXXX)
    trap cleanup EXIT INT TERM
    touch "$MARKER"
}

cleanup() {
    local exit_code=$?
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    if [ -n "${MARKER:-}" ] && [ -f "$MARKER" ]; then
        rm -f "$MARKER"
    fi
    exit "$exit_code"
}
```

---

## 3. The `run_py` Execution Engine

`syncdap` utilizes a 3-tier execution strategy to run internal Python engines without requiring users to manually manage virtual environments:

```bash
# Excerpt from src/sh/common.sh
run_py() {
    if [ -n "${SYNCDAP_PYTHON:-}" ] && [ -x "$SYNCDAP_PYTHON" ]; then
        "$SYNCDAP_PYTHON" "$@"
    elif command -v uv &>/dev/null; then
        uv run --offline --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 "$@" 2>/dev/null || \
        uv run --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 "$@" 2>/dev/null || \
        python3 "$@"
    else
        python3 "$@"
    fi
}
```

1. **Explicit Environment (`SYNCDAP_PYTHON`):** If defined and executable, executes directly.
2. **`uv` Isolated Cache:** If `uv` is installed, runs via `uv run --offline` using cached wheels. If offline cache fails, allows online wheel fetch.
3. **System `python3` Fallback:** Executes directly with host Python if `uv` is not present.

---

## 4. Dual-Audience Error Formatting (`error_dual`)

`common.sh` implements standard Dual-Audience error messaging for all fatal command failures:

```bash
error_dual() {
    local title="$1"
    local message="$2"
    local command_usage="$3"
    local raw_output="${4:-}"
    local recommendation="${5:-}"

    echo -e "${RED}${ICON_ERR} ${BOLD}Error: ${title}${RESET}" >&2
    echo -e "   ${message}" >&2
    if [ -n "$command_usage" ]; then
        echo -e "   Usage: ${CYAN}${command_usage}${RESET}" >&2
    fi
    if [ -n "$recommendation" ]; then
        echo -e "   ${YELLOW}${recommendation}${RESET}" >&2
    fi
    if [ -n "$raw_output" ] && [ "$VERBOSE" = true ]; then
        echo -e "\n${DIM}--- Diagnostic Trace ---" >&2
        echo -e "${raw_output}${RESET}\n" >&2
    fi
}
```
All human diagnostics are sent to `stderr` (`>&2`), preserving `stdout` for JSON and plain Unix pipelines.

---

## Summary & Next Steps
With execution safety guaranteed, we explore how `downloader.sh` wraps external audio ingestion binaries while trapping failures.

---

> **The Syncdap Book Navigation:** [← Previous Section](03-shell-orchestrator.md) • [Table of Contents](../index.md) • [Next Section →](05-shell-downloader.md)
