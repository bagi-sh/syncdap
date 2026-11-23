# Rockbox Hardware & Audio Model

Rockbox is an open-source replacement firmware for digital audio players. It enforces specific constraints that `syncdap` is optimized to satisfy.

---

## 1. Split Album Prevention (`ALBUMARTIST`)

### The Problem
When building its internal database, Rockbox indexes tracks by `ALBUM`. If tracks in the same directory contain varying `ARTIST` tags (common in collaborations, featured artists, or soundtracks) and lack an identical `ALBUMARTIST` tag, Rockbox splits the album into separate entries in its database browser.

### The Solution (`src/modules/rockbox_tags.py`)
`syncdap` scans every folder and derives a canonical album artist from directory naming or majority track tags. It writes an identical `ALBUMARTIST` tag across all tracks in the folder, preventing split albums completely.

---

## 2. Standalone `cover.jpg` vs. Embedded Artwork

### DAP RAM Constraints
Embedded ID3 artwork frames can weigh between 500 KB and 5 MB per audio file. On resource-constrained DAPs (such as iPods with 32 MB or 64 MB of RAM), decoding large embedded JPEG/PNG tags on every track change consumes valuable memory and slows database indexing.

### The Solution (`src/modules/covers.py`)
Rockbox natively looks for a local image file named `cover.jpg`, `folder.jpg`, or `albumart.jpg` inside the album directory.
* `syncdap covers optimize` extracts the highest quality artwork to a single `cover.jpg` per album folder.
* It strips heavy embedded artwork tags from the audio files, saving disk space and reducing RAM overhead during playback.

---

## 3. ID3v2.3 vs. ID3v2.4 Compatibility

Rockbox provides optimal tag parsing with **ID3v2.3 (UTF-16)** frames. Some modern taggers write ID3v2.4 with UTF-8, which can result in garbled text or unindexed tags on older DAP builds. `syncdap` writes ID3v2.3 tags with standard encoding for full firmware compatibility.

---

## 4. Playback Logging & `.scrobbler.log` Firmware Quirks

Certain community builds and modern device ports of Rockbox (e.g., Innioasis Y1, Android-based DAP ports, or custom iPod revisions) have known flaws when generating `.scrobbler.log`:

### 1. Inaccurate `#TZ` Header Directive
* **The Problem:** Even when the user configures their local timezone in Rockbox settings (e.g., UTC-3), some builds write the device's local wall-clock time into the timestamp field while hardcoding `#TZ/UTC` in the header directive. If a scrobbler strictly honors `#TZ/UTC`, all scrobbles are submitted with shifted timestamps (e.g. 3 hours into the future), causing Last.fm timeline discrepancies.
* **The Solution:** `syncdap` intentionally **does not blindly trust `#TZ` from the log header**. By default, it infers the host computer's local timezone offset (or accepts an explicit `--timezone` / `--tz-offset` / `scrobbler.tz_offset` in config) and overwrites the header `#TZ` directive to normalize timestamps accurately to UTC.

### 2. Preservation of Repeated / Duplicate Scrobbles
* **The Problem:** Generic scrobbler tools often deduplicate tracks by discarding consecutive or identical `(artist, track)` entries within the same log, assuming they are duplicates or buffer flush glitches.
* **The Solution:** Rockbox users often listen to the same song repeatedly or place tracks on repeat. `syncdap` strictly preserves and uploads every listened playback entry (`rating == "L"`), ensuring no authentic scrobbles are lost. Deduplication is applied only across runs against the persistent watermark timestamp (`scrobbler.state`) to guard against unremoved logs on read-only DAPs.

