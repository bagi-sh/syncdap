# Python Module: scrobbler Subsystem (`src/scrobbler/`)

`src/scrobbler/` is the dedicated synchronization and management subsystem for Rockbox `.scrobbler.log` playback files, interfacing with Last.fm's Audioscrobbler 2.0 API.

---

## 1. Architectural Components

- `cli.py`: Routes scrobbler actions (`sync`, `auth`, `status`, `logout`).
- `parser.py`: Robust TSV parser for Audioscrobbler v1.1 log format with timezone heuristics.
- `client.py`: Last.fm Web Services v2.0 client with MD5 request signing (`api_sig`) and 50-track batching.
- `state.py`: Manages watermark tracking (`scrobbler.state`), credentials (`lastfm.conf`), and rotated log archives (`~/.config/syncdap/logs/`).
- `auth.py`: Desktop Web Authentication token exchange and browser launching.

---

## 2. Synchronization Pipeline & Filtering Contracts

When executing `syncdap scrobbler sync`:

```text
Rockbox .scrobbler.log on DAP
             │
             ▼
   Parse Log Rows (8 TSV columns)
             │
             ├─► Filter 1: Rating check (rating == "L", drops "S" skips)
             ├─► Filter 2: Watermark check (timestamp > last_synced_ts)
             ├─► Filter 3: 14-Day Cutoff (now - timestamp <= 14 * 86400)
             └─► Timezone Normalization (Applies UTC offset compensation)
             │
             ▼
   Chunk into Batches of 50 Tracks
             │
             ▼
   Dispatch POST track.scrobble to Last.fm (250ms inter-batch delay)
             │
             ├── [200 OK] Update watermark in scrobbler.state
             └── [Offline] Retain pending scrobbles for next run
             │
             ▼
   Archive & Rotate .scrobbler.log on DAP
```

---

## 3. The 14-Day Last.fm Hard Cutoff

Last.fm strictly rejects any scrobble with a timestamp older than **14 days** ($14 \times 86400 = 1,209,600\text{ seconds}$). 

`parser.py` evaluates every entry against the current epoch:
```python
# From src/scrobbler/parser.py
FOURTEEN_DAYS_SECONDS = 14 * 86400

if (now - entry.timestamp) > FOURTEEN_DAYS_SECONDS:
    # Flagged as expired, dropped to prevent API error code 29
```
Expired entries are logged as warnings and archived locally without submitting to Last.fm.

---

## 4. State Persistence & Atomic Watermark

The sync state is recorded in `~/.config/syncdap/scrobbler.state`:
```json
{
  "last_synced_ts": 1731884400,
  "last_run_utc": "2026-11-23T00:00:00Z",
  "submitted_count": 42
}
```
State writes use atomic file replacement (`write -> fsync -> rename`), ensuring the watermark is never corrupted during sudden disconnects.

---

## 5. CLI Invocations

```bash
# Sync playback history from mounted DAP
syncdap scrobbler -r /mnt/dap

# Authenticate with Last.fm
syncdap scrobbler auth

# View scrobbler account and sync status
syncdap scrobbler status
```
