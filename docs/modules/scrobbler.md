# Module Reference: scrobbler (`src/scrobbler/`)

The `scrobbler` module manages Rockbox `.scrobbler.log` parsing, Last.fm Desktop Web Services v2.0 authentication, batch submissions, and deduplication watermarks.

---

## Architecture Overview

```text
src/scrobbler/
├── __init__.py      # Package export interface
├── auth.py          # Desktop authentication flow & browser handoff
├── client.py        # Last.fm API client, MD5 signature generator, batch submitter
├── parser.py        # Audioscrobbler v1.0 / v1.1 log parser & timezone handler
├── state.py         # Human-editable INI/conf credential and watermark persistence
└── cli.py           # Standalone argparse CLI entrypoint
```

---

## Key Components

### 1. Audioscrobbler Log Parser (`parser.py`)
* Reads `.scrobbler.log` adhering to Audioscrobbler v1.0 and v1.1 specifications.
* Filters out skipped tracks (`rating != "L"`).
* **Firmware Quirk Mitigation (Timezone)**: Certain Rockbox port builds (such as modern Innioasis or customized target builds) hardcode `#TZ/UTC` into the log header despite the DAP's RTC and playback timestamps being set to local time (e.g., UTC-3). `syncdap` ignores/overwrites the header `#TZ` directive by default using the host machine's timezone, or by explicit user configuration (`--timezone`, `--tz-offset`, or `scrobbler.tz_offset`).
* **Preservation of Repeated Scrobbles**: Disables intra-log deduplication. Users frequently repeat songs; all listened playback instances (`rating == "L"`) are submitted to Last.fm.
* **14-Day Expiration Guard**: Identifies and isolates tracks older than Last.fm's 14-day limit without halting valid tracks.
* **Watermark Deduplication**: Skips entries with `timestamp <= last_scrobbled_timestamp` across runs to prevent re-submitting historical plays if `.scrobbler.log` was not removed from the DAP.

---

## Rockbox Firmware Build Quirks & Design Decisions

Rockbox is an open-source firmware ported across dozens of varied hardware targets by different maintainers. Not all ports implement the Audioscrobbler specification flawlessly:

1. **`#TZ/UTC` Overwrite Decision**:
   Several target ports write `#TZ/UTC` regardless of the player's actual RTC timezone setting. If trusted, scrobbles end up shifted by several hours on Last.fm. To prevent this, `syncdap` overwrites `#TZ` using the host workstation's local timezone (or explicit `--timezone` / `--tz-offset` parameter).
2. **Duplicate Scrobbles**:
   Do not confuse repeated listening with log corruption. Repeated plays of the same song are legitimate and common; `syncdap` treats all entries with `L` rating as authentic plays.
3. **Encoding Resilience**:
   Some builds write ID3/Vorbis strings with non-standard UTF-8 bytes to the log. `syncdap` parses using `encoding="utf-8", errors="replace"` to ensure the parser never crashes.

### 2. Last.fm API Client (`client.py`)
* Implements strict ASCII/byte lexicographical request signing (`api_sig = md5(sorted(params) + secret)`).
* Chunks scrobbles into batches of up to 50 tracks.
* Parses individual and batch results (`accepted` / `ignored`).

### 3. Desktop Authentication (`auth.py`)
* Obtains temporary token via `auth.getToken`.
* Directs user to browser authorization URL.
* Polls `auth.getSession` every 2.5 seconds with graceful handling of `TokenPendingError` (code 14).
* Stores session in `~/.config/syncdap/lastfm.conf` with `0600` permissions.

### 4. State & Backup Management (`state.py`)
* Stores watermark in `~/.config/syncdap/scrobbler.state`.
* Archives processed logs in `~/.config/syncdap/logs/scrobbler_<YYYY-MM-DD_HHMMSS>.log`.
