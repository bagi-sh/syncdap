#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#     "pykakasi>=2.2.1",
#     "mutagen>=1.47.0",
# ]
# ///

import os
import sys
import shutil
from pathlib import Path

# If pykakasi is not installed in current environment, auto-delegate to uv run
try:
    import pykakasi
    import mutagen
except ImportError:
    if shutil.which("uv"):
        os.execvp("uv", ["uv", "run", "--with", "pykakasi,mutagen", "python3", str(Path(__file__).resolve())] + sys.argv[1:])
    else:
        print("Error: Missing pykakasi or mutagen. Please install them or install uv.")
        sys.exit(1)

# Add lib directory to path
script_dir = Path(__file__).resolve().parent
lib_dir = script_dir / "lib"
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from romaji import main

if __name__ == "__main__":
    main()
