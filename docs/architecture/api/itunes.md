# External API: iTunes Search API

`syncdap` queries the Apple iTunes Search API for fast, high-quality audio metadata resolution and duration lookups.

---

## 1. Endpoints & Queries

* **Base URL:** `https://itunes.apple.com/search`
* **Query Parameters:**
  * `term`: Encoded artist and track or album name.
  * `entity`: Filtered to `song` or `album`.
  * `limit`: Typically `5` to minimize network overhead.

---

## 2. Usage in syncdap

* **Duration Verification (`src/modules/audit.py`):** Compares local track durations against iTunes official durations to detect full-album rips.
* **Metadata Search (`src/modules/search.py`):** Resolves canonical album names, release years, and track titles.
* **High-Resolution Artwork (`src/share/covers.py`):** Replaces default `100x100bb.jpg` artwork URLs with `1200x1200bb.jpg` for crisp DAP album art.
