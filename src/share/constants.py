# ==============================================================================
# Module: src/share/constants.py
# Purpose: Shared system constants, audio formats, and ignored directory names
# ==============================================================================

# Supported audio extensions across all modules
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

LOSSLESS_EXTENSIONS = ('.flac', '.wav')
LOSSY_EXTENSIONS = ('.m4a', '.opus', '.ogg', '.mp3')

# System, filesystem, and player directories to ignore during library traversal
IGNORED_DIRS = {
    'lost.dir',
    '.trash-1000',
    '.trash',
    'system volume information',
    '.android_secure',
    '.rockbox',
    'backup',
    '__pycache__',
    '.git',
    'playlists',
    'lib',
}
