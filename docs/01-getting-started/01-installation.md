# Chapter 1.1: Installation, Toolchains & Dependencies

> **The Syncdap Book Navigation:** [← Previous Section](../index.md) • [Table of Contents](../index.md) • [Next Section →](02-configuration.md)

---

## Pedagogical Context & Prerequisites
Welcome to **The Syncdap Book**. This opening section walks you through preparing your host system, installing runtime toolchains, and verifying required multimedia binaries (`ffmpeg`, `yt-dlp`, and `uv`).

---

This guide walks you through setting up `syncdap` on a Linux system.

---

## 1. System Prerequisites

`syncdap` coordinates shell scripts with Python media engines and system audio transcoders. Ensure your system provides the following:

| Dependency | Purpose | Package / Command |
|---|---|---|
| **Bash 4.0+** | Script execution coordinator | Included in standard Linux distributions |
| **Python 3.10+** | Tagging, analytics, audio analysis | `python3 --version` |
| **ffmpeg** | Audio transcoding and stream processing | `sudo apt install ffmpeg` / `pacman -S ffmpeg` |
| **yt-dlp** | Stream extraction fallback engine | `sudo apt install yt-dlp` / `pip install yt-dlp` |
| **uv** *(recommended)* | Isolated, fast Python dependency execution | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **curl & grep** | API queries and text processing | Included in standard Linux distributions |

---

## 2. Installing syncdap

### Option A: Via `uv tool` (Recommended)

`syncdap` provides a standard `pyproject.toml` distribution with all dependencies managed in an isolated environment:

```bash
# Install directly from the GitHub repository:
uv tool install git+https://github.com/bagi-sh/syncdap.git

# Or install from a local clone:
uv tool install .
```

To update to the newest bleeding-edge rolling-release commit:
```bash
syncdap update
# or: uv tool upgrade syncdap
```

---

### Option B: Standalone Lean Installer (Linux, macOS, WSL)

If you prefer a direct Unix installation, the installer installs only the lean runtime code (`src/` and the `syncdap` coordinator) to `~/.local/share/syncdap` with a symlink in `~/.local/bin/syncdap`. It never bloats your system with `.git` history or documentation files (<1 MB total).

#### 1-Line Remote Install
```bash
curl -fsSL https://raw.githubusercontent.com/bagi-sh/syncdap/main/install.sh | bash
```

#### From a Local Clone
```bash
git clone https://github.com/bagi-sh/syncdap.git
cd syncdap
./install.sh
```

#### Bleeding-Edge Rolling Updates
The installed `syncdap` keeps track of rolling-release commits without needing a permanent `.git` directory:
```bash
syncdap update
```

---

### Option C: Manual Portable Setup

---

## 3. Updating syncdap

To update `syncdap` to the latest commit on `main`:
```bash
./syncdap update
```
This fetches the latest code and ensures dependencies are up-to-date.

---

## 4. Uninstallation

To remove `syncdap` and its local symlinks:
```bash
# If symlinked into ~/.local/bin:
rm -f ~/.local/bin/syncdap

# Optionally remove persistent user configuration:
rm -rf ~/.config/syncdap

# Remove repository directory:
cd .. && rm -rf syncdap
```

---

## Summary & Next Steps
Now that your host environment is equipped with `syncdap` and its multimedia toolchains, proceed to the next section to configure your DAP mount points, persistent preferences, and terminal glyphs.

---

> **The Syncdap Book Navigation:** [← Previous Section](../index.md) • [Table of Contents](../index.md) • [Next Section →](02-configuration.md)
