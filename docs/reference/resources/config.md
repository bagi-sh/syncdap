# Resource Reference: config

The `config` resource manages persistent settings stored in `~/.config/syncdap/config`.

---

## 1. Syntax

```text
syncdap config [action]
syncdap config <key>=<value>
```

---

## 2. Invocations

### Inspecting Settings
```bash
# List all active configuration settings
syncdap config list
```

### Modifying Settings
```bash
# Direct key=value syntax
syncdap config icons=true
syncdap config threads=8
syncdap config format=flac
syncdap config root_dir=/mnt/dap/Music

# Alternative set syntax
syncdap config set icons true
```

### Retrieving a Setting
```bash
syncdap config get root_dir
```

### Initializing Configuration
```bash
# Generates a default config file if none exists
syncdap config init
```
