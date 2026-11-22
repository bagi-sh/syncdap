# External API: MusicBrainz & Cover Art Archive

MusicBrainz provides open, comprehensive music metadata and canonical entity relationships.

---

## 1. Endpoints & Schema

* **Base URL:** `https://musicbrainz.org/ws/2/`
* **Cover Art Archive:** `https://coverartarchive.org/release/`
* **Rate Limiting:** Enforces polite querying (1 request per second with a custom `User-Agent` header).

---

## 2. Usage in syncdap

* **Genre Resolution (`src/modules/genres.py`):** Queries release-group and artist tags to populate missing genre metadata.
* **Secondary Track Search (`src/modules/search.py`):** Acts as fallback metadata resolver when iTunes does not index independent or Japanese releases.
* **Release Normalization:** Normalizes compilations and multi-artist releases to prevent split albums.
