# Python Shared Package: share

The `src/share/` package provides reusable core utilities for audio file handling, metadata normalization, iconography, and text formatting.

---

## 1. Modules Breakdown

* **`share.audio` (`src/share/audio.py`):**
  * `find_audio_files(root_dir)`: Universal recursive audio file scanner that seamlessly handles directory paths or single file paths.
  * `get_audio_metadata(fpath)`: Unified metadata reader returning duration, bitrate, sample rate, title, artist, album, album artist, and track numbers across FLAC, MP3, M4A, OGG, OPUS, and WAV.
  * `write_audio_metadata(...)`: Atomic tag writer enforcing ID3v2.3 compliance.
* **`share.icons` (`src/share/icons.py`):**
  * `ICONS`: Dataclass exporting monochromatic Nerd Font, Safe Unicode, and ASCII symbols.
  * `detect_nerd_font()`: Auto-detection checking font registries, environment variables (`NO_COLOR`), and TTY connectivity.
* **`share.text` (`src/share/text.py`):**
  * `clean_string()`: Strips illegal FAT32 characters, normalizes whitespace, and prevents invalid filesystem characters.
  * `parse_filename_metadata()`: Heuristic parser deriving artist and track title from filenames when metadata tags are missing.
* **`share.covers` (`src/share/covers.py`):**
  * Helper functions for detecting and extracting embedded cover artwork frames.
* **`share.api` (`src/share/api.py`):**
  * Rate-limited HTTP client helper for querying metadata APIs with appropriate user-agent headers.
