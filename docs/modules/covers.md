# Python Module: covers.py

`src/modules/covers.py` optimizes album artwork for Rockbox and portable DAPs by extracting standalone `cover.jpg` files and stripping heavy embedded tag artwork.

---

## 1. Capabilities

* **Extraction (`optimize` mode):** Extracts embedded ID3/Vorbis cover art to an external, high-resolution `cover.jpg` in the album directory.
* **Tag Stripping:** Cleans embedded APIC/METADATA_BLOCK_PICTURE frames from audio files to save DAP RAM and disk space.
* **Tag Embedding (`embed` mode):** Inversely embeds local `cover.jpg` directly into audio file tags for players that lack directory cover art support.

---

## 2. Invocation

`covers.py` is called internally by the orchestrator (`syncdap covers optimize` or `syncdap covers embed`) by generating a temporary directory list:

```bash
# Recommended high-level interface:
./syncdap covers optimize
./syncdap covers embed

# Direct internal script execution:
python3 src/modules/covers.py optimize dirs_list.txt 4
python3 src/modules/covers.py embed dirs_list.txt 4
```
