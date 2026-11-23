# Python Module: romaji Subsystem (`src/romaji/`)

`src/romaji/` transliterates Japanese audio metadata, synchronized lyrics, and filesystem paths from Kanji, Hiragana, and Katakana into Latin **Romaji** using `pykakasi`, ensuring readability on hardware DAPs without Japanese font sets.

---

## 1. Character Transliteration Rules

The transliteration engine adheres to modified Hepburn Romanization:
- **Kanji / Kana Conversion:** Transliterates characters to Latin letters with clean spacing.
- **Particle Lowercasing:** Particles and small grammatical words (`no`, `wo`, `wa`, `ga`, `ni`, `to`, `de`, `mo`, `kara`, `made`) are retained in lowercase in the middle of titles.
- **Okurigana Preservation:** Verb and adjective inflection endings (e.g. `ta`, `te`, `nai`, `masu`) are joined cleanly to kanji stems without awkward whitespace.

```python
# From src/romaji/translit.py
PARTICLES = {
    'no', 'wo', 'wa', 'ga', 'ni', 'to', 'de', 'mo', 'na', 'he', 'e',
    'kara', 'made', 'in', 'on', 'at', 'of', 'and', 'the', 'a', 'an'
}
```

---

## 2. Multi-Target Transliteration Scope

When running `syncdap library romaji`:
1. **Audio Tags (`src/romaji/tags.py`):** Rewrites `artist`, `title`, `album`, and `albumartist` tags using Mutagen.
2. **Synchronized Lyrics (`src/romaji/lyrics.py`):** Reads companion `.lrc` files, transliterating lyric lines while strictly preserving timing brackets (`[mm:ss.xx]`).
3. **Filesystem Paths:** Renames files and directories using FAT32-safe Latin names.
4. **Playlists (`src/romaji/playlist.py`):** Updates playlist references to reflect renamed audio paths.

---

## 3. CLI Invocations

```bash
# Transliterate entire music library
syncdap library romaji -r /mnt/dap/Music

# Transliterate a specific artist directory
syncdap artist romaji "RADWIMPS" -r /mnt/dap/Music

# Non-destructive simulation
syncdap library romaji -r /mnt/dap/Music --dry-run
```
