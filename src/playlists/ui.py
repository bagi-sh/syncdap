"""Terminal text styling and table formatting for playlists."""

import shutil
import subprocess


def select_with_fzf(items, prompt="Select > ", header="", multi=False, preview_cmd=None):
    """Interactive selector helper using fzf or fallback number prompt."""
    if not items:
        return [] if multi else None

    if shutil.which('fzf'):
        cmd = ['fzf', '--prompt', prompt]
        if header:
            cmd.extend(['--header', header])
        if multi:
            cmd.extend(['--multi', '--bind', 'alt-a:select-all,alt-d:deselect-all'])
        if preview_cmd:
            cmd.extend(['--preview', preview_cmd, '--preview-window', 'down:3:wrap'])

        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate(input='\n'.join(items))
        if proc.returncode == 0 and out.strip():
            selected = [l.strip() for l in out.strip().splitlines() if l.strip()]
            return selected if multi else selected[0]
        return [] if multi else None

    print(f"\n{header or prompt}")
    for i, it in enumerate(items, 1):
        print(f"  [{i}] {it}")
    choice = input("Enter number (or press Enter to cancel): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        chosen = items[int(choice) - 1]
        return [chosen] if multi else chosen
    return [] if multi else None
