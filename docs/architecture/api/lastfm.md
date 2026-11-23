# API Architecture: Last.fm Web Services v2.0

`syncdap` interfaces with Last.fm's Audioscrobbler 2.0 API for desktop authentication and batch scrobbling.

---

## 1. Authentication Flow (`auth.*`)

Desktop authentication utilizes a three-step token exchange without requiring callback servers or manual copy-pasting:

```text
syncdap                   Last.fm API                   Browser / User
   │                           │                              │
   │─── auth.getToken ────────>│                              │
   │<── token (60m validity) ──│                              │
   │                                                          │
   │─── Open auth URL ───────────────────────────────────────>│
   │                                                          │ (User clicks "Yes, allow access")
   │                                                          │
   │─── auth.getSession (poll) >│                              │
   │<── Code 14 (Pending) ─────│                              │
   │    ... (every 2.5s)       │                              │
   │─── auth.getSession (poll) >│                              │
   │<── 200 OK (session.key) ──│                              │
   │                                                          │
```

### Credentials Storage
* Location: `~/.config/syncdap/lastfm.conf`
* Permissions: `0600` (read/write by owner only)
* Format: Plain human-editable INI (`username = ...`, `session_key = ...`)

---

## 2. Request Signing (`api_sig`)

All authenticated API requests require an MD5 signature computed as:
1. Filter out `format` and `callback` parameters.
2. Sort parameter keys in ascending ASCII/byte lexicographical order.
3. Concatenate each key and value without delimiters (`key1value1key2value2...`).
4. Append `API_SECRET`.
5. Compute MD5 hexadecimal digest in lowercase.

---

## 3. Scrobble Batching (`track.scrobble`)

* Supports up to **50 tracks per POST request**.
* Parameters are indexed using zero-based brackets (`artist[0]`, `track[0]`, `timestamp[0]`).
* Rate limiting: Sequential batches include a 250ms inter-batch delay to respect API limits.
