# Python Module: search.py

`src/modules/search.py` queries metadata APIs to search for tracks and albums by name.

---

## 1. Capabilities

* **Metadata Lookups:** Resolves track titles, artist names, album titles, track counts, and official release years via the Apple iTunes Search API and MusicBrainz.
* **Direct Ingestion Handoff:** Provides resolved track information directly to `fallback.py` to facilitate immediate download.
* **Machine-Readable Outputs:** Supports `--json` and `--plain` (tab-delimited) output flags for scripting and pipe integrations.

---

## 2. CLI Usage

```bash
# Search and return JSON metadata
python3 src/modules/search.py "The Beatles Abbey Road" --json

# Human-readable search result
python3 src/modules/search.py "Daft Punk Discovery"
```
