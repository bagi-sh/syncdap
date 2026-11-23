# Shell Coordinator: icons.sh

`src/sh/icons.sh` handles terminal capability detection, color styling, and exports monochromatic status glyphs tailored for standard terminal emulators and Nerd Font environments.

---

## 1. Iconography Tiers & Glyphs

`icons.sh` defines three distinct representation tiers:

| Concept | Variable | Tier 2: Nerd Font (Opt-In) | Tier 1: Safe Unicode (Default TTY) | Tier 0: ASCII (Piped / NO_COLOR) |
|---|---|---|---|---|
| **Success** | `ICON_OK` | `\U000f012c` (`󰄬`) | `✓` | `[OK]` |
| **Error** | `ICON_ERR` | `\U000f0156` (`󰅖`) | `✗` | `[ERR]` |
| **Warning** | `ICON_WARN` | `\U000f0026` (`󰀦`) | `!` | `[WARN]` |
| **Info** | `ICON_INFO` | `\U000f01d9` (`󰇙`) | `•` | `*` |
| **Music / Track** | `ICON_MUSIC`| `\U000f0386` (`󰎆`) | `♫` | `[TRK]` |
| **Album / Disc** | `ICON_DISC` | `\U000f0ea2` (`󰺢`) | `◎` | `[ALB]` |
| **Download** | `ICON_DL` | `\U000f01da` (`󰇚`) | `↓` | `[DL]` |
| **Playlist** | `ICON_PL` | `\U000f0cb8` (`󰲸`) | `≡` | `[PL]` |
| **Cover / Image** | `ICON_IMG` | `\U000f02e9` (`󰋩`) | `□` | `[IMG]` |
| **Search / Find** | `ICON_FIND` | `\U000f0349` (`󰍉`) | `?` | `[FIND]` |
| **Arrow** | `ICON_ARROW`| `\U000f0142` (`󰅂`) | `→` | `->` |
| **Ellipsis** | `ICON_ELLIPSIS`| `…` | `…` | `...` |

---

## 2. Automatic Detection & Degradation Protocol

The initialization function `init_iconography` detects the output stream environment and selects the appropriate tier:

```bash
# Excerpt from src/sh/icons.sh
init_iconography() {
    local force_icons="${FORCE_ICONS:-auto}"
    local cfg_icons="${CONFIG_ICONS:-auto}"

    # Determine color enablement
    if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-}" != "dumb" ]; then
        BOLD="\033[1m"
        DIM="\033[2m"
        RESET="\033[0m"
        GREEN="\033[1;32m"
        RED="\033[1;31m"
        YELLOW="\033[1;33m"
        BLUE="\033[1;34m"
        CYAN="\033[1;36m"
        MAGENTA="\033[1;35m"
    fi

    # Degrade to ASCII if piped or dumb terminal
    if [ ! -t 1 ] || [ "${TERM:-}" = "dumb" ] || [ "${force_icons}" = "false" ]; then
        ICON_OK="[OK]"
        ICON_ERR="[ERR]"
        ICON_WARN="[WARN]"
        ICON_INFO="*"
        ICON_MUSIC="[TRK]"
        ICON_DISC="[ALB]"
        ICON_DL="[DL]"
        ICON_PL="[PL]"
        ICON_IMG="[IMG]"
        ICON_FIND="[FIND]"
        ICON_ARROW="->"
        ICON_ELLIPSIS="..."
    fi
}
```

### Precedence Hierarchy
1. Explicit CLI flag: `--icons` (forces Tier 2 / 1) or `--no-icons` (forces Tier 0 ASCII).
2. Configuration setting: `icons=true` or `icons=false` in `~/.config/syncdap/config`.
3. POSIX Environment checks:
   - If stdout is not a TTY (`! -t 1`), degrades to Tier 0.
   - If `NO_COLOR` is present or `TERM=dumb`, colors are completely disabled.
