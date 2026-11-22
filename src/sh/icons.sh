#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/icons.sh
# Purpose: Terminal capability & Nerd Font detection with monochromatic symbols
# ==============================================================================

# Global symbol variables
ICON_OK="✓"
ICON_ERR="✗"
ICON_WARN="!"
ICON_INFO="•"
ICON_MUSIC="♫"
ICON_DISC="◎"
ICON_DL="↓"
ICON_PL="≡"
ICON_TAG="•"
ICON_IMG="□"
ICON_FIND="?"
ICON_ARROW="→"
ICON_ELLIPSIS="…"

# Color variables (suppressed if NO_COLOR or !isatty)
BOLD=""
DIM=""
RESET=""
GREEN=""
RED=""
YELLOW=""
BLUE=""
CYAN=""
MAGENTA=""

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

    # Check ASCII degradation
    if [ ! -t 1 ] || [ "${TERM:-}" = "dumb" ]; then
        ICON_OK="[OK]"
        ICON_ERR="[ERR]"
        ICON_WARN="[WARN]"
        ICON_INFO="[INFO]"
        ICON_MUSIC="[TRK]"
        ICON_DISC="[ALB]"
        ICON_DL="[DL]"
        ICON_PL="[PL]"
        ICON_TAG="[TAG]"
        ICON_IMG="[IMG]"
        ICON_FIND="[FIND]"
        ICON_ARROW="->"
        ICON_ELLIPSIS="..."
        return 0
    fi

    # Evaluate Nerd Font support
    local has_nerd=false
    if [ "$force_icons" = "true" ] || [ "$cfg_icons" = "true" ] || [ "${SYNCDAP_ICONS:-}" = "nerdfont" ]; then
        has_nerd=true
    elif [ "$force_icons" = "false" ] || [ "$cfg_icons" = "false" ] || [ "${SYNCDAP_ICONS:-}" = "none" ]; then
        has_nerd=false
    elif command -v fc-list >/dev/null 2>&1 && fc-list : family 2>/dev/null | grep -iq "nerd"; then
        has_nerd=true
    elif [ "${NERD_FONTS:-0}" = "1" ] || [[ "${TERM_PROGRAM:-}" =~ (WezTerm|Ghostty|kitty|Alacritty) ]]; then
        has_nerd=true
    fi

    if [ "$has_nerd" = true ]; then
        # Tier 2: Monochromatic Nerd Font Glyphs
        ICON_OK="󰄬"
        ICON_ERR="󰅖"
        ICON_WARN="󰀦"
        ICON_INFO="󰇙"
        ICON_MUSIC="󰎆"
        ICON_DISC="󰺢"
        ICON_DL="󰇚"
        ICON_PL="󰲸"
        ICON_TAG="󰓹"
        ICON_IMG="󰋩"
        ICON_FIND="󰍉"
        ICON_ARROW="󰁔"
        ICON_ELLIPSIS="…"
    else
        # Tier 1: Safe Unicode (Default interactive)
        ICON_OK="✓"
        ICON_ERR="✗"
        ICON_WARN="!"
        ICON_INFO="•"
        ICON_MUSIC="♫"
        ICON_DISC="◎"
        ICON_DL="↓"
        ICON_PL="≡"
        ICON_TAG="•"
        ICON_IMG="□"
        ICON_FIND="?"
        ICON_ARROW="→"
        ICON_ELLIPSIS="…"
    fi
}

error_dual() {
    local headline="$1"
    local cause="${2:-}"
    local target="${3:-}"
    local state="${4:-}"
    local fix="${5:-}"

    echo -e "${RED}${ICON_ERR} ${headline}${RESET}" >&2
    [ -n "$cause" ]  && echo -e "  ${DIM}Cause:${RESET}  ${cause}" >&2
    [ -n "$target" ] && echo -e "  ${DIM}Target:${RESET} ${target}" >&2
    [ -n "$state" ]  && echo -e "  ${DIM}State:${RESET}  ${state}" >&2
    if [ -n "$fix" ]; then
        echo -e "  ${DIM}Fix:${RESET}    ${fix}" >&2
    fi
}
