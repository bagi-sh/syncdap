#!/usr/bin/env uv run
# /// script
# dependencies = [
#     "pykakasi>=2.2.1",
#     "mutagen>=1.47.0",
# ]
# ///

import os
import sys
from pathlib import Path

# Add lib directory to path
script_dir = Path(__file__).resolve().parent
lib_dir = script_dir / "lib"
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from romaji import main

if __name__ == "__main__":
    main()
