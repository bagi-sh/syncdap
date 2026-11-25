# Chapter 7.3: String Normalization & FAT32 Sanitization (`text.py`)

> **The Syncdap Book Navigation:** [← Previous Section](02-audio-engine.md) • [Table of Contents](../index.md) • [Next Section →](04-constants-and-runtime.md)

---

## Pedagogical Context & Prerequisites
In Chapter 2.2, we established that FAT32 storage volumes reject specific punctuation characters and truncate paths exceeding 255 bytes. Here, we inspect `src/share/text.py`, the module responsible for guaranteeing filesystem safety and normalized fuzzy string matching.

---

## 1. FAT32 Character Substitution

`sanitize_filename(name, for_folder=False)` replaces prohibited VFS characters and full-width Japanese punctuation with safe ASCII equivalents:

```python
# From src/share/text.py
SYMBOL_REPLACEMENTS = {
    '℃': 'C', '℉': 'F', '＆': '&', '％': '%', '＋': '+',
    '・': ' ', '…': '...', '、': ', ', '。': '', '！': '!',
    '？': '?', '：': ': ', '　': ' ',
}
```

- **Illegal Characters Stripped:** `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`.
- **Trailing Edge Rule:** Strips trailing periods (`.`) and whitespace (` `) to prevent Windows/VFS truncation panics.

---

## 2. Fuzzy String Normalization for Match Audits

When comparing metadata across iTunes, MusicBrainz, and local filenames, variations in capitalization, punctuation, and spacing must be reconciled:

```python
# From src/share/text.py
def normalize_str(s: str) -> str:
    """Normalize string for loose title/artist matching (lowercase, stripped punctuation/spaces)."""
    if not s:
        return ""
    s = str(s).lower().strip()
    s = re.sub(r'[\s_\-]+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()
```

- Converts `"The Beatles - Let It Be (Remastered 2009)"` and `"Let It Be"` into unified tokens for duration and track title comparison.

---

## Summary & Next Steps
`text.py` ensures that all generated paths strictly obey FAT32 limitations. In the next section, we study global constants, HTTP connection pooling, and terminal icon formatting.

---

> **The Syncdap Book Navigation:** [← Previous Section](02-audio-engine.md) • [Table of Contents](../index.md) • [Next Section →](04-constants-and-runtime.md)
