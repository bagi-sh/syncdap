# Resource Reference: tags

The `tags` resource provides audio metadata standardization, multi-API genre enrichment, and Romaji transliteration.

---

## 1. Syntax

```text
syncdap tags <action> [target] [options]
```

---

## 2. Actions

### `fix`
Standardizes `ALBUM` and `ALBUMARTIST` metadata across album directories, eliminates split albums in Rockbox, and deletes zero-byte ghost files.
```bash
syncdap tags fix
syncdap tags fix -n
```

### `genres`
Queries the Apple iTunes Search API, Deezer, and MusicBrainz to enrich missing genre metadata tags across tracks.
```bash
syncdap tags genres
```

### `romaji`
Transliterates Japanese Kanji, Hiragana, and Katakana in metadata tags, file paths, and `.lrc` files to Hepburn Romaji.
```bash
# Transliterate entire library
syncdap tags romaji

# Transliterate target folder or file
syncdap tags romaji "/path/to/Japanese_Album"
```
