#!/usr/bin/env python3
# ==============================================================================
# Module: lib/patch.py
# Purpose: Entry point for audio quality patch and upgrade operations
# ==============================================================================

import os
import sys
from pathlib import Path

lib_dir = Path(__file__).resolve().parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

from patch.cli import main

if __name__ == '__main__':
    main()
