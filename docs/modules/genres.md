# Python Module: genres.py

`src/modules/genres.py` enriches missing genre metadata tags across audio tracks by querying multiple external APIs in priority order.

---

## 1. Capabilities

* **Multi-API Fallback:**
  1. Apple iTunes Search API (fast release-level genre lookup).
  2. Deezer API (broad contemporary music coverage).
  3. MusicBrainz (canonical community genre tags).
* **Tag Writing:** Updates ID3 `TCON`, Vorbis `GENRE`, and MP4 `©gen` metadata tags without altering other fields.
* **Concurrency:** Runs multi-threaded worker pools to process large album folders quickly.

---

## 2. Invocation

`genres.py` is invoked through `syncdap tags genres`, which compiles target directories into a temporary file:

```bash
# Recommended high-level interface:
./syncdap tags genres

# Direct internal module execution:
python3 src/modules/genres.py album_dirs.txt 4
```
