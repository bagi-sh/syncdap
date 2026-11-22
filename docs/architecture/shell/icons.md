# Shell Coordinator: icons.sh

`src/sh/icons.sh` handles terminal capability detection and exports monochromatic status glyphs.

---

## 1. Iconography Tiers

`icons.sh` automatically detects terminal capabilities and provides three clean tiers:

| Concept | Tier 2: Nerd Font (Opt-In / Detected) | Tier 1: Safe Unicode (Default TTY) | Tier 0: ASCII (Piped / NO_COLOR) |
|---|---|---|---|
| **Success** | `󰄬` (`\U000f012c`) | `✓` | `[OK]` |
| **Error** | `󰅖` (`\U000f0156`) | `✗` | `[ERR]` |
| **Warning** | `󰀦` (`\U000f0026`) | `!` | `[WARN]` |
| **Info** | `󰇙` (`\U000f01d9`) | `•` | `*` |
| **Music / Track** | `󰎆` (`\U000f0386`) | `♫` | `[TRK]` |
| **Album / Disc** | `󰺢` (`\U000f0ea2`) | `◎` | `[ALB]` |
| **Download** | `󰇚` (`\U000f01da`) | `↓` | `[DL]` |
| **Playlist** | `󰲸` (`\U000f0cb8`) | `≡` | `[PL]` |
| **Cover / Image** | `󰋩` (`\U000f02e9`) | `□` | `[IMG]` |
| **Search / Find** | `󰍉` (`\U000f0349`) | `?` | `[FIND]` |

---

## 2. Detection Strategy

Symbols degrade automatically based on environment variables:
1. `--icons` or `--no-icons` CLI flag.
2. `icons` key in `~/.config/syncdap/config`.
3. If `NO_COLOR` is set, `TERM=dumb`, or standard output is not a terminal (`! -t 1`), the system automatically falls back to plain ASCII.
