"""Terminal iconography and monochromatic symbol management."""

import os
import subprocess
import sys
from dataclasses import dataclass

from .config import get_config_value


@dataclass(frozen=True)
class IconSet:
    ok: str
    err: str
    warn: str
    info: str
    music: str
    disc: str
    dl: str
    pl: str
    tag: str
    img: str
    find: str
    arrow: str
    ellipsis: str


_NERD_ICONS = IconSet(
    ok="󰄬",
    err="󰅖",
    warn="󰀦",
    info="󰇙",
    music="󰎆",
    disc="󰺢",
    dl="󰇚",
    pl="󰲸",
    tag="󰓹",
    img="󰋩",
    find="󰍉",
    arrow="󰁔",
    ellipsis="…",
)

_UNICODE_ICONS = IconSet(
    ok="✓",
    err="✗",
    warn="!",
    info="•",
    music="♫",
    disc="◎",
    dl="↓",
    pl="≡",
    tag="•",
    img="□",
    find="?",
    arrow="→",
    ellipsis="…",
)

_ASCII_ICONS = IconSet(
    ok="[OK]",
    err="[ERR]",
    warn="[WARN]",
    info="[INFO]",
    music="[TRK]",
    disc="[ALB]",
    dl="[DL]",
    pl="[PL]",
    tag="[TAG]",
    img="[IMG]",
    find="[FIND]",
    arrow="->",
    ellipsis="...",
)


def _detect_nerd_font() -> bool:
    cfg = get_config_value("icons", "auto").lower()
    if cfg in ("true", "1", "yes", "nerdfont"):
        return True
    if cfg in ("false", "0", "no", "none"):
        return False

    env_val = os.environ.get("SYNCDAP_ICONS", "").lower()
    if env_val == "nerdfont":
        return True
    if env_val == "none":
        return False

    if os.environ.get("NERD_FONTS", "0") == "1":
        return True

    term_prog = os.environ.get("TERM_PROGRAM", "")
    if any(t in term_prog for t in ("WezTerm", "Ghostty", "kitty", "Alacritty")):
        return True

    try:
        res = subprocess.run(
            ["fc-list", ":", "family"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if "nerd" in res.stdout.lower():
            return True
    except Exception:
        pass

    return False


def get_icons() -> IconSet:
    # 1. ASCII fallback for non-interactive / NO_COLOR / dumb
    if not sys.stdout.isatty() or os.environ.get("TERM") == "dumb":
        return _ASCII_ICONS

    # 2. Check Nerd Font
    if _detect_nerd_font():
        return _NERD_ICONS

    # 3. Default Safe Unicode
    return _UNICODE_ICONS


ICONS = get_icons()


def format_error_dual(
    headline: str,
    cause: str | None = None,
    target: str | None = None,
    state: str | None = None,
    fix: str | None = None,
) -> str:
    icons = get_icons()
    lines = [f"{icons.err} {headline}"]
    if cause:
        lines.append(f"  Cause:  {cause}")
    if target:
        lines.append(f"  Target: {target}")
    if state:
        lines.append(f"  State:  {state}")
    if fix:
        lines.append(f"  Fix:    {fix}")
    return "\n".join(lines)
