#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/config.sh
# Purpose: Configuration management for syncdap (~/.config/syncdap/config)
# ==============================================================================

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/syncdap"
if ! mkdir -p "$CONFIG_DIR" 2>/dev/null; then
    CONFIG_DIR="$PWD/.config/syncdap"
fi
CONFIG_FILE="$CONFIG_DIR/config"

load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        while IFS='=' read -r key val || [ -n "$key" ]; do
            # Trim whitespace
            key="$(echo "$key" | tr -d '[:space:]')"
            val="$(echo "$val" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
            # Ignore comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [ -z "$key" ] && continue

            case "$key" in
                icons)      CONFIG_ICONS="$val" ;;
                threads)    CONFIG_THREADS="$val" ;;
                format)     CONFIG_FORMAT="$val" ;;
                root_dir)   CONFIG_ROOT_DIR="$val" ;;
                synced_only) CONFIG_SYNCED_ONLY="$val" ;;
            esac
        done < "$CONFIG_FILE"
    fi
}

get_config() {
    local target_key="$1"
    if [ -f "$CONFIG_FILE" ]; then
        grep "^${target_key}=" "$CONFIG_FILE" 2>/dev/null | head -n 1 | cut -d'=' -f2-
    fi
}

set_config() {
    local key="$1"
    local val="$2"

    mkdir -p "$CONFIG_DIR"
    touch "$CONFIG_FILE"

    if grep -q "^${key}=" "$CONFIG_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$CONFIG_FILE"
    else
        echo "${key}=${val}" >> "$CONFIG_FILE"
    fi
}

handle_config_command() {
    local action="${1:-}"

    if [ -z "$action" ] || [ "$action" = "list" ] || [ "$action" = "show" ]; then
        echo "Current configuration (${CONFIG_FILE}):"
        if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
            cat "$CONFIG_FILE"
        else
            echo "  (No configuration set. Defaults in use.)"
        fi
        return 0
    fi

    # Handle key=value syntax (e.g., syncdap config icons=true)
    if [[ "$action" == *"="* ]]; then
        local key="${action%%=*}"
        local val="${action#*=}"
        set_config "$key" "$val"
        echo "✓ Configuration saved: ${key} = ${val}"
        return 0
    fi

    case "$action" in
        set)
            if [ $# -lt 3 ]; then
                echo "✗ Error: 'config set' requires key and value (e.g. syncdap config set icons true)" >&2
                return 2
            fi
            set_config "$2" "$3"
            echo "✓ Configuration saved: $2 = $3"
            ;;
        get)
            if [ $# -lt 2 ]; then
                echo "✗ Error: 'config get' requires a key name" >&2
                return 2
            fi
            local val
            val="$(get_config "$2")"
            if [ -n "$val" ]; then
                echo "$val"
            else
                echo "✗ Key '$2' is not set." >&2
                return 1
            fi
            ;;
        init)
            mkdir -p "$CONFIG_DIR"
            if [ ! -f "$CONFIG_FILE" ]; then
                cat << 'EOF' > "$CONFIG_FILE"
# syncdap configuration
icons=auto
threads=4
format=flac
EOF
                echo "✓ Initialized configuration at: $CONFIG_FILE"
            else
                echo "! Configuration file already exists at: $CONFIG_FILE"
            fi
            ;;
        *)
            # Check if second arg exists for key value syntax
            if [ $# -ge 2 ]; then
                set_config "$1" "$2"
                echo "✓ Configuration saved: $1 = $2"
            else
                echo "✗ Unknown config action: $action" >&2
                echo "Usage: syncdap config [key=value | set <key> <val> | get <key> | list]" >&2
                return 2
            fi
            ;;
    esac
}
