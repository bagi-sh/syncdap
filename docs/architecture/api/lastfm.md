# External API: Last.fm Web Services v2.0

`src/scrobbler/` implements the complete Last.fm Audioscrobbler 2.0 desktop authentication flow, cryptographic request signing, and batch scrobble synchronization for Rockbox players.

---

## 1. Network Protocol & Cryptographic Invariants

- **API Endpoint:** `https://ws.audioscrobbler.com/2.0/`
- **Format:** JSON (`format=json`)
- **Default Credentials:** Sourced from `src/share/constants.py` or overridden via environment variables:
  ```python
  LASTFM_API_KEY = os.getenv("SYNCDAP_LASTFM_API_KEY", "968d453baa45e579a864cb6f9cb145ef")
  LASTFM_API_SECRET = os.getenv("SYNCDAP_LASTFM_API_SECRET", "a6253b76b199de52509870c4881cd2db")
  ```

---

## 2. Request Signing Algorithm (`api_sig`)

Every authenticated POST/GET request to Last.fm requires a 32-character lowercase MD5 signature computed over all request parameters:

```python
# From src/scrobbler/client.py
def get_api_signature(params: dict[str, Any], secret: str = LASTFM_API_SECRET) -> str:
    """Compute Last.fm API signature (api_sig) using MD5."""
    # 1. Filter out format and callback parameters
    filtered = {k: v for k, v in params.items() if k not in ("format", "callback")}
    
    # 2. Sort keys in ascending ASCII byte order
    sorted_keys = sorted(filtered.keys())
    
    # 3. Concatenate key and string value without delimiters
    raw_sig = "".join(f"{k}{filtered[k]}" for k in sorted_keys)
    
    # 4. Append shared secret
    raw_sig += secret
    
    # 5. Compute MD5 hexadecimal digest
    return hashlib.md5(raw_sig.encode("utf-8")).hexdigest()
```

---

## 3. Desktop Authentication Protocol (`src/scrobbler/auth.py`)

Last.fm desktop clients authenticate without hosting a local web server:

```text
syncdap                   Last.fm API                   Browser / User
   │                           │                              │
   │─── auth.getToken ────────>│                              │
   │<── token (60m validity) ──│                              │
   │                                                          │
   │─── Open auth URL ───────────────────────────────────────>│
   │    https://www.last.fm/api/auth/?api_key=...&token=...   │ (User grants access)
   │                                                          │
   │─── auth.getSession (poll every 2.5s) ───────────────────>│
   │<── HTTP 200 with Error 14 (Unauthorized Token)           │
   │    ...                                                   │
   │─── auth.getSession ─────────────────────────────────────>│
   │<── HTTP 200: session.name, session.key ──────────────────│
   │                                                          │
   ▼
Persist credentials to ~/.config/syncdap/lastfm.conf (chmod 0600)
```

### Credentials File Permissions & State Security
The session file `lastfm.conf` stores the user's permanent session key:
```ini
[lastfm]
username = myuser
session_key = 5a4b3c2d1e0f...
```
It is written using atomic file creation with permissions enforced at `0600` (`-rw-------`), preventing unauthorized local users from reading Last.fm session tokens on shared Linux workstations.

---

## 4. Batch Scrobble Dispatch (`track.scrobble`)

Last.fm supports submitting up to **50 tracks per HTTP POST request**:
- Parameters use zero-indexed array syntax: `artist[0]`, `track[0]`, `timestamp[0]`, `album[0]`, `trackNumber[0]`, `duration[0]`.
- Requests exceeding 50 entries are chunked into separate sequential POST calls.
- **Inter-Batch Delay:** Sequential chunks include a 250ms sleep to avoid API rate-limit rejection.
- **Error Code Handling:**
  - Code `9` (Invalid session key): Clears stored `lastfm.conf` and prompts re-authentication.
  - Code `11` / `16` (Service offline / temporary outage): Retains tracks in `scrobbler.state` for resubmission on the next sync run.
