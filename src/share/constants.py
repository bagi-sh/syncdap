"""Shared constants, supported audio formats, and ignored directories."""

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.opus', '.wav')

LOSSLESS_EXTENSIONS = ('.flac', '.wav', '.aiff', '.ape', '.alac')
LOSSY_EXTENSIONS = ('.m4a', '.opus', '.ogg', '.mp3')

# Standard cover art filenames recognized across modules and players
COVER_FILENAMES = ('cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.jpeg', 'folder.png')

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

# Regex patterns for download filtering and candidate ranking
FULL_ALBUM_PATTERNS = [
    r'\b(full[\s\-_]*album)\b',
    r'\b(album[\s\-_]*completo)\b',
    r'\b(álbum[\s\-_]*completo)\b',
    r'\b(complete[\s\-_]*album)\b',
    r'\b(discography)\b',
    r'\b(discografia)\b',
    r'\b(full[\s\-_]*ep)\b',
    r'\b(full[\s\-_]*tape)\b',
    r'\b(full[\s\-_]*vinyl)\b',
    r'\b(all\s+tracks)\b',
    r'\b(greatest\s+hits(\s+full)?)\b',
    r'\b(best\s+of(\s+full)?)\b',
]

LIVE_PATTERNS = [
    r'\b(ao[\s\-_]*vivo)\b',
    r'\b(en[\s\-_]*vivo)\b',
    r'\b(live(\s+(at|in|from|version|session|acoustic|tour|concert))?)\b',
    r'\b(in\s+concert)\b',
    r'\b(unplugged)\b',
    r'\b(bootleg)\b',
    r'\b(radio\s+broadcast)\b',
    r'\b(tour\s+\d{4})\b',
]

REMIX_PATTERNS = [
    r'\b(re[\s\-_]*mix(ed)?)\b',
    r'\b(club\s+mix)\b',
    r'\b(extended\s+(mix|version))\b',
    r'\b(slowed(\s+(and|\+)\s+reverb)?)\b',
    r'\b(sped[\s\-_]*up)\b',
    r'\b(speed[\s\-_]*up)\b',
    r'\b(nightcore)\b',
    r'\b(daycore)\b',
    r'\b(bass[\s\-_]*boost(ed)?)\b',
    r'\b(instrumental)\b',
    r'\b(karaoke)\b',
    r'\b(cover)\b',
    r'\b(tribute)\b',
    r'\b(parody)\b',
    r'\b(edit)\b',
    r'\b(mashup)\b',
    r'\b(8d\s+audio)\b',
]
