# CLI Reference: Global Syntax & Rules

`syncdap` follows an **Entity-Action** command hierarchy with standard POSIX/GNU flags and strict stream separation.

---

## 1. Syntax Pattern

```text
syncdap <resource> [action] [target] [options]
```

Where:
* `<resource>`: The primary entity being managed (`library`, `artist`, `album`, `track`, `playlist`, `covers`, `lyrics`, `tags`, `scrobbler`, `config`, `download`, `search`, `rescue`).
* `[action]`: The specific operation performed on the entity (e.g., `status`, `dedup`, `audit`, `optimize`, `fix`, `organize`, `patch`, `romaji`).
* `[target]`: Path or query target (optional or required depending on the entity).
* `[options]`: Execution flags modifier.

---

## 2. Standard Global Flags

| Flag | Short | Behavior |
|---|---|---|
| `--help` | `-h` | Output concise help information and exit `0`. |
| `--version` | `-V` | Output semantic version (`syncdap 1.0.0`) and exit `0`. |
| `--verbose` | `-v` | Emit diagnostic telemetry to `stderr`. |
| `--quiet` | `-q` | Suppress non-error status output (`stdout` emits only data or final confirmation). |
| `--dry-run` | `-n` | Simulate execution without modifying filesystem or metadata. |
| `--yes` | `-y` | Automatically confirm interactive prompts. |
| `--root-dir <path>` | `-r` | Target music library or DAP mount root (default: `.`). |
| `--threads <num>` | `-t` | Worker concurrency for audio analysis and downloads (default: `4`). |
| `--format <fmt>` | `-F` | Audio container format: `flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav`. |
| `--json` | | Output structured machine-readable JSON array/object. |
| `--plain` | | Output headerless, tab-delimited plain text for Unix pipelines. |
| `--icons` / `--no-icons` | | Force enable or disable Nerd Font monochromatic symbols. |

---

## 3. Stream Discipline

* **`stdout` (Standard Output):** Reserved for primary command output, tables, JSON data, and single-line success confirmations. Safe for piping:
  ```bash
  syncdap library status --json | jq .
  ```
* **`stderr` (Standard Error):** Progress spinners, download bars, warning diagnostics, and Dual-Audience error formatting.
