#!/usr/bin/env python3
# ==============================================================================
# Module: lib/romaji.py
# Purpose: Entry point for Rockbox Romaji Transliteration
# ==============================================================================

import os
import sys
from pathlib import Path

# Ensure lib directory is in sys.path
lib_dir = Path(__file__).resolve().parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from romaji.cli import main

if __name__ == "__main__":
    main()
