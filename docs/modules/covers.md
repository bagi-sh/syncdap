# Python Module: covers.py

`src/modules/covers.py` optimizes album artwork for Rockbox and portable DAPs by extracting standalone `cover.jpg` files and stripping heavy embedded tag artwork.

---

## 1. Capabilities

* **Extraction (`optimize` mode):** Extracts embedded ID3/Vorbis cover art to an external, high-resolution `cover.jpg` in the album directory.
* **Tag Stripping:** Cleans embedded APIC/METADATA_BLOCK_PICTURE frames from audio files to save DAP RAM and disk space.
* **Tag Embedding (`embed` mode):** Inversely embeds local `cover.jpg` directly into audio file tags for players that lack directory cover art support.

---

## 2. CLI Usage

```bash
# Optimize album covers for Rockbox (extracts cover.jpg and strips embedded art)
python3 src/modules/covers.py optimize dirs_list.txt 4

# Embed local cover.jpg files back into audio tags
python3 src/modules/covers.py embed dirs_list.txt 4
```
