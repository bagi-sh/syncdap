# ==============================================================================
# Module: lib/playlists/cli.py
# Purpose: CLI argument routing for playlist operations
# ==============================================================================

import sys
from .manager import interactive_playlist_manager
from .actions import delete_playlist_flow, merge_playlists_flow


def main():
    if len(sys.argv) < 2:
        interactive_playlist_manager()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == '--delete':
        target = sys.argv[2] if len(sys.argv) > 2 else ""
        yes_flag = '--yes' in sys.argv or '-y' in sys.argv
        sys.exit(delete_playlist_flow(target, yes_flag))
    elif cmd == '--merge':
        pl1 = sys.argv[2] if len(sys.argv) > 2 else ""
        pl2 = sys.argv[3] if len(sys.argv) > 3 else ""
        out_name = None
        del_src = False
        yes_flag = False
        for arg in sys.argv[4:]:
            if arg in ('--delete-sources', '--delete'):
                del_src = True
            elif arg in ('--yes', '-y'):
                yes_flag = True
            elif not arg.startswith('-') and not out_name:
                out_name = arg
        sys.exit(merge_playlists_flow(pl1, pl2, out_name, del_src, yes_flag))
    elif cmd in ('--menu', '-P', '--playlist'):
        sys.exit(interactive_playlist_manager())
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
