#!/usr/bin/env bash
# ==============================================================================
# Script: install.sh
# Purpose: Unified installer, updater, and uninstaller for syncdap
# ==============================================================================

set -euo pipefail

# ANSI Color Codes
BOLD="\033[1m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

# Installation defaults
INSTALL_MODE="install"
TARGET_TYPE="user"
CUSTOM_PREFIX=""
ASSUME_YES=false

show_help() {
    cat << EOF
Usage:
  ./install.sh [OPTIONS]

Options:
  --user               Install for current user into ~/.local/share/syncdap and ~/.local/bin (default).
  --system, --root     Install system-wide into /usr/local/share/syncdap and /usr/local/bin (requires root/sudo).
  --prefix <PATH>      Install into custom base directory prefix.
  --update, -u         Pull latest commits from repository and refresh installed tool & cache.
  --uninstall,
  --unistall           Completely uninstall syncdap and remove installed files and symlinks.
  -y, --yes            Assume yes to prompts (non-interactive mode).
  -h, --help           Display this help message and exit.
EOF
}

# --- CLI ARGUMENT PARSING ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)
            TARGET_TYPE="user"
            shift 1
            ;;
        --system|--root)
            TARGET_TYPE="system"
            shift 1
            ;;
        --prefix)
            if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                echo -e "${RED}❌ Error: --prefix requires a directory path.${RESET}" >&2
                exit 1
            fi
            CUSTOM_PREFIX="$2"
            shift 2
            ;;
        --update|-u)
            INSTALL_MODE="update"
            shift 1
            ;;
        --uninstall|--unistall)
            INSTALL_MODE="uninstall"
            shift 1
            ;;
        -y|--yes)
            ASSUME_YES=true
            shift 1
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Error: Unknown option: $1${RESET}" >&2
            echo "Run './install.sh --help' for usage."
            exit 1
            ;;
    esac
done

# Resolve paths
if [ -n "$CUSTOM_PREFIX" ]; then
    INSTALL_DIR="${CUSTOM_PREFIX}/share/syncdap"
    BIN_DIR="${CUSTOM_PREFIX}/bin"
elif [ "$TARGET_TYPE" = "system" ] || [ "$(id -u)" -eq 0 ]; then
    INSTALL_DIR="/usr/local/share/syncdap"
    BIN_DIR="/usr/local/bin"
else
    INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/syncdap"
    BIN_DIR="${HOME}/.local/bin"
fi

# Helper: execute command with privilege escalation if necessary
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo &>/dev/null; then
        sudo "$@"
    else
        echo -e "${RED}❌ Error: Root permissions required for this step, but sudo is unavailable.${RESET}" >&2
        return 1
    fi
}

# --- UNINSTALL FLOW ---
do_uninstall() {
    echo -e "${BOLD}${YELLOW}🗑️  Uninstalling syncdap...${RESET}"
    if [ "$ASSUME_YES" != true ]; then
        read -rp "Are you sure you want to remove syncdap from '$INSTALL_DIR'? [y/N]: " confirm
        case "$confirm" in
            [yY][eE][sS]|[yY]) ;;
            *) echo "Uninstallation aborted."; exit 0 ;;
        esac
    fi

    local bin_launcher="${BIN_DIR}/syncdap"
    if [ -L "$bin_launcher" ] || [ -f "$bin_launcher" ]; then
        echo "Removing launcher: $bin_launcher"
        if [ -w "$BIN_DIR" ]; then
            rm -f "$bin_launcher"
        else
            run_privileged rm -f "$bin_launcher"
        fi
    fi

    if [ -d "$INSTALL_DIR" ]; then
        echo "Removing files: $INSTALL_DIR"
        if [ -w "$(dirname "$INSTALL_DIR")" ]; then
            rm -rf "$INSTALL_DIR"
        else
            run_privileged rm -rf "$INSTALL_DIR"
        fi
    fi

    echo -e "${GREEN}✅ syncdap was successfully uninstalled from your system.${RESET}"
    exit 0
}

if [ "$INSTALL_MODE" = "uninstall" ]; then
    do_uninstall
fi

# --- DEPENDENCY VERIFICATION & SETUP ---
ensure_system_dependencies() {
    echo -e "${CYAN}🔍 Checking required system utilities...${RESET}"
    local missing=()
    for dep in git python3 ffmpeg curl; do
        if ! command -v "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${YELLOW}Missing system dependencies: ${missing[*]}${RESET}"
        echo "Attempting to install via system package manager..."

        if command -v zypper &>/dev/null; then
            run_privileged zypper --non-interactive in "${missing[@]}"
        elif command -v apt-get &>/dev/null; then
            run_privileged apt-get update && run_privileged apt-get install -y "${missing[@]}"
        elif command -v dnf &>/dev/null; then
            run_privileged dnf install -y "${missing[@]}"
        elif command -v pacman &>/dev/null; then
            run_privileged pacman -Sy --noconfirm "${missing[@]}"
        elif command -v apk &>/dev/null; then
            run_privileged apk add "${missing[@]}"
        else
            echo -e "${RED}❌ Could not automatically install: ${missing[*]}.${RESET}"
            echo "Please install them using your system package manager and rerun install.sh."
            exit 1
        fi
    fi
}

ensure_uv() {
    if ! command -v uv &>/dev/null; then
        echo -e "${CYAN}⚡ Installing Astral uv (high-performance Python manager)...${RESET}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
    fi

    if ! command -v uv &>/dev/null; then
        echo -e "${RED}❌ Error: Failed to find or install uv.${RESET}" >&2
        exit 1
    fi
}

build_python_cache() {
    echo -e "${CYAN}⚡ Pre-warming Python dependency cache and runtime wheels...${RESET}"
    uv run --with mutagen,eyed3,requests,pykakasi,syncedlyrics python3 -c \
        "import mutagen, eyed3, requests, pykakasi; print('✅ Python runtime and dependencies verified')" 2>/dev/null || \
    echo -e "${YELLOW}⚠️ Notice: Python cache pre-warm completed with local fallbacks.${RESET}"

    # Ensure spotdl runner is ready
    if ! command -v spotdl &>/dev/null; then
        echo -e "${CYAN}🎵 Setting up spotDL environment...${RESET}"
        uv tool install spotdl 2>/dev/null || true
    fi
}

# --- REPOSITORY UPDATE (GIT PULL) ---
update_git_source() {
    local target_repo="$1"
    if [ -d "$target_repo/.git" ]; then
        echo -e "${CYAN}📥 Pulling newest commits from Git repository in $target_repo...${RESET}"
        if git -C "$target_repo" pull --rebase 2>&1; then
            echo -e "${GREEN}✅ Repository updated to latest version.${RESET}"
        else
            echo -e "${YELLOW}⚠️ Notice: Git pull failed (offline or local changes). Proceeding with current files.${RESET}"
        fi
    fi
}

# --- INSTALL / UPDATE EXECUTION ---
echo -e "${BOLD}${BLUE}🚀 syncdap Installer & Environment Setup${RESET}"
echo "--------------------------------------------------"
echo "Destination Directory: $INSTALL_DIR"
echo "Binary Launcher:       $BIN_DIR/syncdap"
echo "--------------------------------------------------"

# If running from a git clone and update is requested (or running again), pull git first
if [ -d "$SCRIPT_DIR/.git" ]; then
    update_git_source "$SCRIPT_DIR"
fi

ensure_system_dependencies
ensure_uv
build_python_cache

# Create target directories
if [ "$TARGET_TYPE" = "system" ] || [ "$(id -u)" -eq 0 ]; then
    run_privileged mkdir -p "$INSTALL_DIR" "$BIN_DIR"
else
    mkdir -p "$INSTALL_DIR" "$BIN_DIR"
fi

# Copy codebase if script is running from outside the destination directory
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo -e "${CYAN}📦 Installing project files to $INSTALL_DIR...${RESET}"

    # Remove existing files except .git if already present in target
    if [ -d "$INSTALL_DIR" ]; then
        find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name ".git" -exec rm -rf {} + 2>/dev/null || true
    fi

    # Copy code tree
    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/syncdap" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/"
    [ -f "$SCRIPT_DIR/.gitignore" ] && cp "$SCRIPT_DIR/.gitignore" "$INSTALL_DIR/"

    # Preserve .git repository in destination so updates work after deleting original clone
    if [ -d "$SCRIPT_DIR/.git" ]; then
        echo -e "${CYAN}🔗 Preserving Git repository metadata for seamless future updates...${RESET}"
        rm -rf "$INSTALL_DIR/.git"
        cp -a "$SCRIPT_DIR/.git" "$INSTALL_DIR/"
    fi
else
    # SCRIPT_DIR is already INSTALL_DIR (e.g. syncdap --update was called)
    update_git_source "$INSTALL_DIR"
fi

# Set executable permissions
echo -e "${CYAN}🔒 Setting permissions...${RESET}"
chmod +x "$INSTALL_DIR/syncdap" "$INSTALL_DIR/install.sh"
find "$INSTALL_DIR/src/sh" -name "*.sh" -exec chmod +x {} + 2>/dev/null || true

# Create symlink launcher in $BIN_DIR
echo -e "${CYAN}🔗 Creating launcher symlink: $BIN_DIR/syncdap...${RESET}"
ln -sf "$INSTALL_DIR/syncdap" "$BIN_DIR/syncdap"

# PATH verification
echo ""
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}⚠️ Notice: '$BIN_DIR' is not in your current PATH.${RESET}"
    echo "To run syncdap from any terminal, add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    echo ""
fi

echo -e "${BOLD}${GREEN}🎉 syncdap installation/update finished successfully!${RESET}"
echo ""
echo -e "You can now safely ${BOLD}delete${RESET} your downloaded/cloned repository directory:"
echo -e "  rm -rf \"$SCRIPT_DIR\""
echo ""
echo "Getting Started:"
echo "  syncdap --help           # View commands and options"
echo "  syncdap --status         # Check music library dashboard"
echo "  syncdap --update         # Pull newest commits and update syncdap"
echo "  syncdap --uninstall      # Completely remove syncdap from system"
