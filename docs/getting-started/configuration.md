# Configuration & DAP Hardware Mounts

`syncdap` supports both persistent configuration files and runtime CLI overrides.

---

## 1. Persistent Configuration (`~/.config/syncdap/config`)

By default, `syncdap` stores user settings at:
```text
~/.config/syncdap/config
```

You can inspect or modify these settings using `syncdap config`:

### Viewing Configuration
```bash
# Display all active settings and config file location
syncdap config list
```

### Setting Values
```bash
# Force enable Nerd Font monochromatic symbols
syncdap config icons=true

# Set default target audio format
syncdap config format=flac

# Set default worker threads concurrency
syncdap config threads=4

# Set default music library or DAP mount root
syncdap config root_dir=/mnt/dap/Music
```

### Initializing Default Configuration
```bash
syncdap config init
```

---

## 2. Configuration Key Reference

| Key | Valid Options | Default | Description |
|---|---|---|---|
| `icons` | `true`, `false`, `auto` | `auto` | Controls terminal symbol rendering (Nerd Font vs Safe Unicode vs ASCII). |
| `threads` | Integer (`1`–`16`) | `4` | Concurrency for audio analysis, lyrics searches, and stream processing. |
| `format` | `flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav` | `flac` | Target format for downloads, transcodes, and album expansions. |
| `root_dir` | Valid directory path | `.` (current directory) | Default path when `-r` is not explicitly passed. |
| `synced_only` | `true`, `false` | `false` | Accept only timestamped `[mm:ss]` synchronized lyrics files. |

---

## 3. DAP Hardware Mount Points

When connecting an offline Digital Audio Player (DAP) running Rockbox or generic firmware:

1. **Mount your DAP filesystem:**
   ```bash
   # Example: DAP mounted at /mnt/dap
   ls /mnt/dap
   ```
2. **Execute syncdap targeting the DAP mount:**
   Pass the mount path using the `-r` flag:
   ```bash
   # Check DAP storage and tag integrity
   syncdap library status -r /mnt/dap/Music

   # Run complete Rockbox optimization directly on DAP
   syncdap library optimize -r /mnt/dap/Music
   ```
3. **Persist the DAP mount:**
   If you regularly sync to the same mount:
   ```bash
   syncdap config root_dir=/mnt/dap/Music
   ```
   Now `syncdap library status` automatically analyzes `/mnt/dap/Music` without needing `-r` every time.
