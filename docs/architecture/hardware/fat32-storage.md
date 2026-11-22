# FAT32 Storage & Path Constraints

Most Digital Audio Players (DAPs) use SD cards or internal flash storage formatted as **FAT32** or **exFAT**.

---

## 1. Path Length Limits

FAT32 filesystems enforce a maximum path length of 260 characters (`MAX_PATH`). Long artist names, elaborate album subtitles, or deeply nested folder structures can exceed this limit, causing file write errors or corrupted database entries on the DAP.

`syncdap` mitigates this through clean string parsing (`src/share/text.py`), truncating long paths safely while preserving essential track identifiers.

---

## 2. Forbidden Characters

FAT32 forbids the following characters in directory and file names:
```text
\ / : * ? " < > |
```

`syncdap` sanitizes metadata before creating files or folders, replacing forbidden characters with safe Unicode or ASCII equivalents (e.g., `:` replaced with `-` or space).

---

## 3. Case Insensitivity

FAT32 is case-insensitive but case-preserving. Deduplication and playlist relinking routines account for case insensitivity so paths match accurately across Linux host machines and the player's internal index.
