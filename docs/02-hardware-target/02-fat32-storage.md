# Chapter 2.2: FAT32 Storage Constraints & VFS Limits

> **The Syncdap Book Navigation:** [← Previous Section](01-rockbox-model.md) • [Table of Contents](../index.md) • [Next Section →](../03-architecture-and-runtime/01-two-tier-model.md)

---

## Pedagogical Context & Prerequisites
In the previous section, we explored Rockbox's memory architecture. In this section, we examine the storage media: SD cards and microdrives formatted with FAT32 or exFAT, their 255-byte path limits, illegal character sets, and case-insensitivity.

---

Digital Audio Players (DAPs), microSD cards, and Rockbox target drives are predominantly formatted with **FAT32** (or **exFAT** for cards $\ge 64\text{ GB}$). FAT32 enforces rigid filesystem constraints that will trigger unhandled OS errors, file corruption, or database dropouts if ignored.

---

## 1. Path Length Limits (`MAX_PATH = 260`)

FAT32 filesystems and the Windows/POSIX driver interfaces for FAT volume mounts enforce a maximum path limit of **260 characters** (`MAX_PATH`). 

In modern music libraries, deeply nested folder structures combined with verbose classical or Japanese titles routinely exceed this limit:
```text
/mnt/dap/Music/The Alan Parsons Project/Tales of Mystery and Imagination (Edgar Allan Poe) [Deluxe Edition]/01 A Dream Within a Dream (Remastered 1987) - The Alan Parsons Project.flac
Total length: 271 characters -> Triggers ENAMETOOLONG / Errno 36
```

### Mitigation Strategy (`src/share/text.py`)
`syncdap` implements deterministic truncation on filenames:
- It isolates the audio extension (`.mp3`, `.flac`).
- It limits the directory component to 120 characters and the file stem to 100 characters.
- It guarantees that track numbers (e.g. `01 `) and artist stems are preserved, preventing collisions when names are shortened.

---

## 2. Forbidden Characters & Sanitization Protocol

FAT32 forbids 9 ASCII characters in directory and file names:
```text
\  /  :  *  ?  "  <  >  |
```

In addition, trailing dots (`.`) and trailing spaces (` `) are illegal under FAT32 directory table specifications and can cause files to become invisible or undeletable on Linux host mounts.

### Symbol Replacement Map (`src/share/text.py`)
`syncdap` intercepts every path before creation and transforms illegal characters into visually similar Unicode or clean ASCII equivalents:

```python
# From src/share/text.py
SYMBOL_REPLACEMENTS = {
    '℃': 'C',
    '℉': 'F',
    '＆': '&',
    '％': '%',
    '＋': '+',
    '・': ' ',
    '…': '...',
    '、': ', ',
    '。': '',
    '！': '!',
    '？': '?',
    '：': ': ',
    '　': ' ',
}

def sanitize_filename(name: str, for_folder: bool = False) -> str:
    """Sanitize name for FAT32 / exFAT filesystems removing illegal characters."""
    if not name:
        return name

    # 1. Substitute full-width Unicode punctuation
    for orig, repl in SYMBOL_REPLACEMENTS.items():
        name = name.replace(orig, repl)

    # 2. Replace FAT32 illegal characters
    name = re.sub(r'[\/\\:\*\?"<>\|]', '_', name)

    # 3. Strip trailing dots and whitespace
    name = re.sub(r'[\.\s]+$', '', name)

    return name.strip()
```

---

## 3. Case Insensitivity vs. Case Preservation

FAT32 is **case-insensitive but case-preserving**:
- `Queen` and `queen` refer to the same directory on the FAT32 volume.
- Attempting to rename `/mnt/dap/Music/QUEEN` to `/mnt/dap/Music/Queen` using a naive `os.rename()` fails or does nothing because the filesystem treats the source and destination as identical.

### Collision Prevention in Deduplication
When comparing tracks during `syncdap dedup` or `syncdap fix`:
1. File matching uses normalized lower-case keys: `(normalize_str(stem), track_num)`.
2. When renaming directories or audio files for case corrections on FAT32, `syncdap` uses a two-phase rename via an intermediate temporary name (`Queen` $\to$ `Queen__tmp_rename` $\to$ `queen`) to prevent filesystem collision rejections.

---

## 4. Atomic State File Writes & Flash Safety

Writing state files (e.g. `scrobbler.state`, playlist modifications, or ID3 tags) directly to a FAT32 filesystem over USB carries high risks of corruption if the cable is detached or if the DAP buffer runs out of power.

`syncdap` enforces atomic file replacement (`write -> fsync -> rename`):
```python
def atomic_save(file_path: Path, content: str):
    temp_path = file_path.with_suffix(".tmp." + str(os.getpid()))
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())  # Flush hardware write buffers on USB device
    os.replace(temp_path, file_path)  # Atomic rename
```

This guarantees that `scrobbler.state` or playlists on the DAP can never be left in a half-written or zero-byte state.

---

## Summary & Next Steps
Now that you understand the dual hardware constraints—Rockbox's RAM/database indexing and FAT32's filesystem limits—we are ready to explore how `syncdap` is architected to survive and thrive in this environment.

---

> **The Syncdap Book Navigation:** [← Previous Section](01-rockbox-model.md) • [Table of Contents](../index.md) • [Next Section →](../03-architecture-and-runtime/01-two-tier-model.md)
