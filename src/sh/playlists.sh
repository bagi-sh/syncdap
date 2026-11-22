#!/usr/bin/env bash
# ==============================================================================
# Module: src/sh/playlists.sh
# Purpose: Playlist mapping and relative UTF-8 M3U8 processing
# ==============================================================================

process_playlists() {
    local is_playlist=false
    if [[ -n "$CLEAN_URL" && "$CLEAN_URL" =~ /playlist/ ]]; then
        is_playlist=true
    fi

    # Standard playlist directory: sibling ../Playlists (both PC ~/Playlists and DAP /sdcard/Playlists)
    local pl_dir="../Playlists"
    if ! mkdir -p "$pl_dir" 2>/dev/null; then
        pl_dir="Playlists"
        mkdir -p "$pl_dir" 2>/dev/null || true
    fi

    if [ "$is_playlist" = true ]; then
        if [ "$QUIET" = false ]; then
            echo -e "${CYAN}${ICON_PL} [2/5] Mapping playlist (.m3u8) and adjusting relative paths...${RESET}" >&2
        fi

        shopt -s nullglob
        local m3u_files=( *.m3u8 *.m3u )
        shopt -u nullglob

        if [ ${#m3u_files[@]} -gt 0 ]; then
            for f in "${m3u_files[@]}"; do
                local dest="$pl_dir/$f"
                if [[ "$dest" =~ \.m3u$ ]]; then
                    dest="${dest%*.m3u}.m3u8"
                fi

                mv -f "$f" "$dest"

                python3 - "$dest" << 'EOF'
import sys, os
path = sys.argv[1]
try:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    out = []
    has_header = False
    pl_dir = os.path.dirname(os.path.abspath(path))
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('#EXTM3U'):
            has_header = True
            out.append(s)
        elif s.startswith('#'):
            out.append(s)
        else:
            clean = s
            if clean.startswith('../Music/'):
                clean = clean[9:]
            elif clean.startswith('../'):
                clean = clean[3:]
            elif clean.startswith('./'):
                clean = clean[2:]
            
            song_abs = os.path.abspath(clean)
            rel_entry = os.path.relpath(song_abs, pl_dir)
            out.append(rel_entry)
    if not has_header:
        out.insert(0, '#EXTM3U')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
except Exception as e:
    print(f"  ! Could not format playlist {path}: {e}", file=sys.stderr)
EOF
                if [ "$QUIET" = false ]; then
                    echo -e "   ${GREEN}${ICON_OK} Playlist mapped:${RESET} $dest" >&2
                fi
                if [ -z "$TARGET_M3U" ]; then
                    TARGET_M3U="$dest"
                fi
            done
        else
            if [ "$QUIET" = false ]; then
                echo -e "   ${ICON_INFO} No new M3U8 playlists found in this session." >&2
            fi
        fi
    else
        if [ "$QUIET" = false ]; then
            echo -e "${ICON_PL} [2/5] Album or single track detected. Skipping playlist generation." >&2
        fi
        rm -f *.m3u *.m3u8 2>/dev/null || true
    fi
}
