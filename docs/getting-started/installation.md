# Installation & Setup

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

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/syncdap.git
   cd syncdap
   ```

2. **Make the entrypoint executable:**
   ```bash
   chmod +x syncdap
   ```

3. **Verify the environment:**
   Run the health check to verify all dependencies and your Python runtime:
   ```bash
   ./syncdap library status
   ```

4. **Optional: Add to system PATH:**
   To invoke `syncdap` from any directory:
   ```bash
   mkdir -p ~/.local/bin
   ln -s "$(pwd)/syncdap" ~/.local/bin/syncdap
   ```
   Ensure `~/.local/bin` is in your `PATH` (in `~/.bashrc` or `~/.zshrc`):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

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
