# Shell Coordinator: config.sh

`src/sh/config.sh` manages persistent user configuration stored in standard XDG user configuration directories, injecting defaults into the runtime environment prior to CLI dispatch.

---

## 1. Storage Location & Precedence

The configuration file is resolved according to the following precedence hierarchy:
1. Custom file specified via `-c <path>` or `--config <path>`.
2. `$XDG_CONFIG_HOME/syncdap/config` (if `$XDG_CONFIG_HOME` is set).
3. `~/.config/syncdap/config` (standard user home).
4. `$PWD/.config/syncdap/config` (project-local fallback if user home is read-only).

```bash
# Excerpt from src/sh/config.sh
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/syncdap"
if ! mkdir -p "$CONFIG_DIR" 2>/dev/null; then
    CONFIG_DIR="$PWD/.config/syncdap"
fi
CONFIG_FILE="$CONFIG_DIR/config"
```

---

## 2. Configuration File Grammar & Parser Specification

The file uses a clean `key=value` format. Lines starting with `#` and empty lines are discarded:

```ini
# syncdap configuration
icons=true
threads=8
format=flac
root_dir=/mnt/dap/Music
synced_only=true
```

### Parser Implementation (`load_config`)
```bash
# Excerpt from src/sh/config.sh
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key val || [ -n "$key" ]; do
            key="$(echo "$key" | tr -d '[:space:]')"
            val="$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            [[ "$key" =~ ^#.*$ ]] && continue
            [ -z "$key" ] && continue

            case "$key" in
                icons)       CONFIG_ICONS="$val" ;;
                threads)     CONFIG_THREADS="$val" ;;
                format)      CONFIG_FORMAT="$val" ;;
                root_dir)    CONFIG_ROOT_DIR="$val" ;;
                synced_only) CONFIG_SYNCED_ONLY="$val" ;;
            esac
        done < "$CONFIG_FILE"
    fi
}
```

---

## 3. Supported Configuration Keys

| Key | Valid Values | Runtime Default | Description |
|---|---|---|---|
| `icons` | `true`, `false`, `auto` | `auto` | Controls Nerd Font / Unicode icon rendering in terminal |
| `threads` | Integer (`1` to `32`) | `4` | Concurrency worker count for downloads and audio scans |
| `format` | `flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav` | `mp3` | Target audio format for downloads and transcoding |
| `root_dir` | Valid directory path | `.` | Default music root or DAP mount point |
| `synced_only` | `true`, `false` | `false` | If true, lyrics engines discard unsynchronized plain lyrics |

---

## 4. Atomic Key Modification (`set_config`)

When writing configuration updates via `syncdap config <key>=<val>`:
- If the key exists, `sed -i` replaces the value in place.
- If the key is new, it is appended to the configuration file.
- Directory and file creation are ensured with `mkdir -p` and `touch`.
