# Python Subsystem: romaji

The `src/romaji/` subsystem provides Japanese Kanji and Kana transliteration to Hepburn Romaji across tags, filenames, and lyrics.

---

## 1. Package Structure

* `src/romaji/cli.py` – CLI argument parser.
* `src/romaji/engine.py` – File system traversal and batch transliteration coordinator.
* `src/romaji/translit.py` – `pykakasi` integration for converting Kanji, Hiragana, and Katakana to Hepburn Romaji.
* `src/romaji/tags.py` – ID3, Vorbis, and MP4 tag transliteration without overwriting non-Japanese characters.
* `src/romaji/lyrics.py` – Transliterates `.lrc` lyrics while strictly preserving `[mm:ss.xx]` timing tags.
* `src/romaji/playlist.py` – Updates `.m3u` / `.m3u8` entries when files or directories are renamed to Romaji.

---

## 2. Invocations

```bash
# Transliterate entire library to Romaji
python3 src/romaji/cli.py -r /path/to/music -a

# Transliterate a specific album folder
python3 src/romaji/cli.py -r /path/to/music -p "/path/to/music/Artist/Album"

# Dry-run inspection
python3 src/romaji/cli.py -r /path/to/music -a -n
```
