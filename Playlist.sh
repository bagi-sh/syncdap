#!/usr/bin/env bash
# ==============================================================================
# Script: Playlist.sh
# Purpose: Interactive M3U/M3U8 playlist creator and editor using fzf
# ==============================================================================

set -uo pipefail

PLAYLIST_DIR="Playlists"
TEMP_SELECTION=$(mktemp -t m3u_builder.XXXXXX 2>/dev/null || mktemp)
TEMP_EXISTING=$(mktemp -t m3u_existing.XXXXXX 2>/dev/null || mktemp)

cleanup() {
    rm -f "$TEMP_SELECTION" "$TEMP_EXISTING"
}
trap cleanup EXIT INT TERM

# --- 1. DEPENDENCY CHECK ---
if ! command -v fzf &>/dev/null; then
    echo "❌ Error: 'fzf' is not installed."
    exit 1
fi

mkdir -p "$PLAYLIST_DIR"

# --- 2. MAIN MENU: CREATE OR EDIT ---
echo "🎵 Interactive M3U8 Playlist Manager"
echo "------------------------------------------"

ACTION=$(printf "1. Create a new playlist\n2. Edit an existing playlist" | \
    fzf --header="[ Choose an action ]" --prompt="Action > ")

if [ -z "$ACTION" ]; then
    echo "⚠️ No action selected. Operation canceled."
    exit 0
fi

PLAYLIST_FILE=""
EXISTING_ITEMS=()

if [[ "$ACTION" =~ ^2 ]]; then
    # --- EDIT MODE ---
    shopt -s nullglob
    M3U_LIST=( "$PLAYLIST_DIR"/*.m3u8 "$PLAYLIST_DIR"/*.m3u )
    shopt -u nullglob

    if [ ${#M3U_LIST[@]} -eq 0 ]; then
        echo "❌ No playlist files found in '$PLAYLIST_DIR/'."
        exit 1
    fi

    SELECTED_M3U=$(printf "%s\n" "${M3U_LIST[@]}" | fzf --header="[ Select playlist to edit ]" --prompt="Playlist > ")
    
    if [ -z "$SELECTED_M3U" ]; then
        echo "⚠️ No playlist selected. Operation canceled."
        exit 0
    fi

    PLAYLIST_FILE=$(basename "$SELECTED_M3U")
    
    # Extract existing tracks removing comments (#) and cleaning ../ prefix
    python3 -c "
import sys
with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        l = line.strip()
        if l and not l.startswith('#'):
            if l.startswith('../'):
                l = l[3:]
            print(l)
" "$SELECTED_M3U" > "$TEMP_EXISTING"

    echo "📖 Playlist '$PLAYLIST_FILE' loaded with $(wc -l < "$TEMP_EXISTING") track(s)."

else
    # --- CREATE MODE ---
    read -rp "Enter new playlist name (e.g. My Favorites): " PLAYLIST_NAME

    if [ -z "$PLAYLIST_NAME" ]; then
        echo "❌ Invalid playlist name."
        exit 1
    fi

    if [[ "$PLAYLIST_NAME" != *.m3u8 ]] && [[ "$PLAYLIST_NAME" != *.m3u ]]; then
        PLAYLIST_FILE="${PLAYLIST_NAME}.m3u8"
    else
        PLAYLIST_FILE="$PLAYLIST_NAME"
    fi
fi

DEST_PATH="$PLAYLIST_DIR/$PLAYLIST_FILE"

# --- 3. TRACK SELECTION WITH FZF ---
echo ""
echo "🔍 Searching audio files in library..."
echo "💡 fzf Tips:"
echo "   - TAB: Select / Deselect track"
echo "   - Alt+A: Select all visible"
echo "   - Enter: Confirm selection"
echo ""

PREVIEW_CMD="echo {}"
if command -v eyeD3 &>/dev/null; then
    PREVIEW_CMD="eyeD3 {} 2>/dev/null || echo {}"
fi

# Map all audio files (.mp3, .flac, .m4a, .ogg, .opus, .wav) ignoring Playlists directory
find . -type f \( -name "*.mp3" -o -name "*.flac" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.opus" -o -name "*.wav" \) ! -path "./Playlists/*" | sed 's|^\./||' | sort | \
fzf --multi \
    --header="[ TAB: Mark/Unmark | Enter: Confirm ]" \
    --prompt="Tracks > " \
    --preview="$PREVIEW_CMD" \
    --preview-window=down:3:wrap \
    --bind="alt-a:select-all,alt-d:deselect-all" > "$TEMP_SELECTION"

if [ ! -s "$TEMP_SELECTION" ] && [ ! -s "$TEMP_EXISTING" ]; then
    echo "⚠️ No tracks selected. Operation canceled."
    exit 0
fi

# Combine existing and new selections without duplicates
if [ -s "$TEMP_EXISTING" ]; then
    cat "$TEMP_EXISTING" "$TEMP_SELECTION" | awk '!seen[$0]++' > "${TEMP_SELECTION}.tmp"
    mv "${TEMP_SELECTION}.tmp" "$TEMP_SELECTION"
fi

# --- 4. REVIEW IN EDITOR ---
echo ""
echo "📋 Total tracks in playlist ($(wc -l < "$TEMP_SELECTION")):"
echo "------------------------------------------"
cat -n "$TEMP_SELECTION"
echo ""

read -rp "Do you want to open in text editor to reorder or remove tracks? [y/N]: " REORDER
REORDER=${REORDER:-N}

if [[ "$REORDER" =~ ^[Yy]$ ]]; then
    EDITOR_BIN="${EDITOR:-nano}"
    echo "Opening in $EDITOR_BIN... (Reorder lines or delete to remove)"
    sleep 1
    "$EDITOR_BIN" "$TEMP_SELECTION"
fi

# --- 5. GENERATE/UPDATE M3U FILE ---
python3 -c "
import sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f if l.strip()]

with open(sys.argv[2], 'w', encoding='utf-8') as f:
    f.write('#EXTM3U\n')
    for line in lines:
        if line.startswith('../'):
            f.write(line + '\n')
        else:
            f.write('../' + line + '\n')
" "$TEMP_SELECTION" "$DEST_PATH"

COUNT=$(grep -c '^[^#]' "$DEST_PATH" || true)

echo ""
echo "✅ Playlist saved successfully!"
echo "📍 File: $DEST_PATH"
echo "🎶 Total tracks: $COUNT"

exit 0
