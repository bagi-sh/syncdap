# Shell Coordinator: config.sh

`src/sh/config.sh` handles persistent user settings and hardware defaults stored in `~/.config/syncdap/config`.

---

## 1. Responsibilities

* **Settings Storage:** Reads and writes simple `key=value` configuration files.
* **XDG Base Directory Compliance:** Defaults to `$XDG_CONFIG_HOME/syncdap/config` (or `~/.config/syncdap/config`).
* **Environment Overrides:** Injects saved configuration defaults (`threads`, `format`, `root_dir`, `icons`) into shell environment variables prior to command execution.

---

## 2. Invocations

```bash
# View configuration file and values
syncdap config list

# Set key=value pairs
syncdap config icons=true
syncdap config threads=8
syncdap config root_dir=/mnt/dap/Music

# Retrieve specific value
syncdap config get format
```
