# Shell Coordinator: cli.sh

`src/sh/cli.sh` governs the CLI grammar, argument parsing loop, help generation, and subaction validation across all `syncdap` invocations.

---

## 1. CLI Grammar Specification

`syncdap` adheres to an **Entity-First** command pattern:
```text
syncdap <resource> [action] [target] [options]
```

Where:
- **`resource`:** The primary operational domain (`library`, `artist`, `album`, `track`, `playlist`, `covers`, `lyrics`, `tags`, `scrobbler`, `config`, `download`, `search`, `rescue`, `status`).
- **`action`:** The verb to execute within that domain (`status`, `audit`, `dedup`, `optimize`, `fix`, `expand`, `patch`, `romaji`, `merge`, `repair`, `manage`).
- **`target`:** Path, artist name, URL, or format string.
- **`options`:** Global and action-specific flags (`-r`, `-t`, `-F`, `-n`, `-v`, `-q`, `--json`, `--plain`, `--icons`, `--no-icons`).

---

## 2. Argument Parsing Loop & Positionals Extraction

The parser uses a POSIX-compliant `while` loop with `getopts`/manual shifting:

```bash
# Simplified structure from src/sh/cli.sh
parse_cli() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                HELP_REQUESTED=true
                shift ;;
            -V|--version)
                echo "syncdap $SYNCDAP_VERSION"
                exit 0 ;;
            -r|--root-dir)
                TARGET_ROOT="$2"
                shift 2 ;;
            -t|--threads)
                THREADS="$2"
                shift 2 ;;
            -F|--format)
                AUDIO_FORMAT="$2"
                shift 2 ;;
            -n|--dry-run)
                DRY_RUN=true
                shift ;;
            --json)
                OUTPUT_FORMAT="json"
                shift ;;
            --plain)
                OUTPUT_FORMAT="plain"
                shift ;;
            -*)
                error_dual "Unknown option" "Flag '$1' is unrecognized" "syncdap --help"
                exit 2 ;;
            *)
                # Collect positionals
                POSITIONALS+=("$1")
                shift ;;
        esac
    done
}
```

### URL Auto-Routing
If the first positional argument is an HTTP/HTTPS URL (e.g. `https://open.spotify.com/album/...`), `cli.sh` automatically rewires the command to `download`:
```bash
if [[ "${POSITIONALS[0]:-}" =~ ^https?:// ]]; then
    SUBCOMMAND="download"
    COMMAND_ARGS=("${POSITIONALS[@]}")
fi
```

---

## 3. Help Generation Architecture

### Top-Level Help (`show_help`)
Invoked when `syncdap -h` or `syncdap --help` is run without subcommands. Summarizes resources and global options in under 45 lines for fast terminal scanning.

### Resource-Specific Help (`show_resource_help <resource>`)
Triggered when running `syncdap <resource> --help` or `syncdap help <resource>`. It isolates the target domain and displays only the relevant actions, flags, and examples:
```bash
syncdap library --help
syncdap album --help
syncdap scrobbler --help
```

---

## 4. Exit Code Guarantees

| Code | Condition | Behavior |
|---|---|---|
| `0` | Success | Normal exit, clean stdout data |
| `1` | Operational Failure | Runtime error (e.g. network timeout, corrupt file, API failure) |
| `2` | Syntax / Argument Error | Missing required positional, unrecognized flag, invalid format |
