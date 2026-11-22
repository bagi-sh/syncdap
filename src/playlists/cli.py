"""CLI argument routing for playlist operations."""

import sys
from pathlib import Path

lib_dir = Path(__file__).resolve().parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from playlists.manager import interactive_playlist_manager
from playlists.actions import delete_playlist_flow, merge_playlists_flow


def main():
    if len(sys.argv) < 2:
        interactive_playlist_manager()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd in ('delete', '--delete'):
        target = sys.argv[2] if len(sys.argv) > 2 else ""
        yes_flag = '--yes' in sys.argv or '-y' in sys.argv
        sys.exit(delete_playlist_flow(target, yes_flag))
    elif cmd in ('merge', '--merge'):
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
    elif cmd in ('manage', '--menu', '-P', '--playlist'):
        target_name = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else None
        sys.exit(interactive_playlist_manager(target_name))
    else:
        print(f"✗ Unknown playlist command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
