# Configuration & DAP Hardware Mounts

`syncdap` supports both persistent configuration files and runtime CLI overrides.

---

## 1. Persistent Configuration (`~/.config/syncdap/config`)

By default, `syncdap` stores user settings at:
```text
~/.config/syncdap/config
```
If `$XDG_CONFIG_HOME` is set, it resolves to `$XDG_CONFIG_HOME/syncdap/config`. If home is read-only, it falls back to `$PWD/.config/syncdap/config`.

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
syncdap config threads=8

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
| `threads` | Integer (`1`–`32`) | `4` | Concurrency for audio analysis, lyrics searches, and stream processing. |
| `format` | `flac`, `mp3`, `m4a`, `opus`, `ogg`, `wav` | `mp3` | Target format for downloads, transcodes, and album expansions. |
| `root_dir` | Valid directory path | `.` (current directory) | Default path when `-r` is not explicitly passed. |
| `synced_only` | `true`, `false` | `false` | Accept only timestamped `[mm:ss]` synchronized lyrics files. |

---

## 3. Scrobbler Credentials & Security (`lastfm.conf`)

Last.fm desktop session credentials are saved separately to:
```text
~/.config/syncdap/lastfm.conf
```
- **Permission Invariant:** Automatically set to `0600` (`-rw-------`).
- **Watermark Persistence:** Synchronization timestamps are maintained in `~/.config/syncdap/scrobbler.state`.
- **Log Rotations:** Archived `.scrobbler.log` files are stored in `~/.config/syncdap/logs/`.

---

## 4. DAP Hardware Mount Points

When connecting an offline Digital Audio Player (DAP) running Rockbox:

1. **Mount your DAP filesystem:**
   ```bash
   sudo mount /dev/sdX1 /mnt/dap
   ```
2. **Execute maintenance directly on the DAP volume:**
   ```bash
   # Sync playback scrobbles
   syncdap scrobbler -r /mnt/dap

   # Complete library optimization
   syncdap library optimize -r /mnt/dap
   ```
3. **Unmount cleanly before disconnecting USB:**
   ```bash
   sync && sudo umount /mnt/dap
   ```
   Ensures FAT32 directory tables and metadata caches are completely flushed.
