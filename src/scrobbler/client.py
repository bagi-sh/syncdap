"""Last.fm API Client and MD5 Signature Generator.

Implements Last.fm Desktop Web Services v2.0:
- Strict lexicographical MD5 request signing (`api_sig`)
- `auth.getToken` and `auth.getSession`
- `track.scrobble` in batches of up to 50 tracks
"""

import hashlib
import json
import time
import urllib.parse
import urllib.request
from typing import Any

from src.scrobbler.parser import ScrobbleEntry
from src.share.constants import LASTFM_API_KEY, LASTFM_API_SECRET

LASTFM_API_ROOT = "https://ws.audioscrobbler.com/2.0/"


class LastFmError(Exception):
    """Raised when Last.fm returns an API error."""

    def __init__(self, code: int, message: str):
        super().__init__(f"Last.fm API error {code}: {message}")
        self.code = code
        self.message = message


class TokenPendingError(LastFmError):
    """Raised when an auth token has not been authorized yet by the user (code 14/16)."""
    pass


def generate_api_sig(params: dict[str, str], secret: str = LASTFM_API_SECRET) -> str:
    """Generate MD5 signature for Last.fm request.

    Sorts all parameter keys strictly in ASCII/byte lexicographical order,
    concatenates `key + value`, appends the API secret, and hashes using MD5.
    Excludes `format` and `callback`.
    """
    filtered = {k: v for k, v in params.items() if k not in ("format", "callback")}
    sorted_keys = sorted(filtered.keys())
    sig_base = "".join(f"{k}{filtered[k]}" for k in sorted_keys) + secret
    return hashlib.md5(sig_base.encode("utf-8")).hexdigest()


def call_api(
    params: dict[str, str],
    is_post: bool = False,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Execute Last.fm API call using standard library urllib."""
    full_params = dict(params)
    if "api_sig" not in full_params:
        full_params["api_sig"] = generate_api_sig(full_params)
    full_params["format"] = "json"

    headers = {
        "User-Agent": "Syncdap/1.0.0 (Linux; Rockbox Sync)",
        "Accept": "application/json",
    }

    if is_post:
        encoded_data = urllib.parse.urlencode(full_params).encode("utf-8")
        req = urllib.request.Request(
            LASTFM_API_ROOT,
            data=encoded_data,
            headers=headers,
            method="POST",
        )
    else:
        url = f"{LASTFM_API_ROOT}?{urllib.parse.urlencode(full_params)}"
        req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            payload = json.loads(data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(error_body)
            code = int(err_json.get("error", e.code))
            msg = err_json.get("message", e.reason)
            if code in (14, 16):
                raise TokenPendingError(code, msg)
            raise LastFmError(code, msg)
        except json.JSONDecodeError:
            raise LastFmError(e.code, f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise LastFmError(0, f"Network connection error: {e.reason}")

    if "error" in payload:
        code = int(payload["error"])
        msg = payload.get("message", "Unknown error")
        if code in (14, 16):
            raise TokenPendingError(code, msg)
        raise LastFmError(code, msg)

    return payload


def get_token() -> str:
    """Request temporary authorization token from Last.fm via auth.getToken."""
    res = call_api({"method": "auth.getToken", "api_key": LASTFM_API_KEY})
    token = res.get("token")
    if not token:
        raise LastFmError(0, "Did not receive valid token from auth.getToken")
    return token


def get_session(token: str) -> dict[str, str]:
    """Exchange authorized token for a permanent session key via auth.getSession."""
    res = call_api({
        "method": "auth.getSession",
        "api_key": LASTFM_API_KEY,
        "token": token,
    })
    session = res.get("session", {})
    name = session.get("name")
    key = session.get("key")
    if not name or not key:
        raise LastFmError(0, "Invalid session response received from Last.fm")
    return {"name": name, "key": key}


def scrobble_batch(
    session_key: str,
    tracks: list[ScrobbleEntry],
) -> dict[str, Any]:
    """Submit a single batch of up to 50 tracks via track.scrobble."""
    if not tracks:
        return {"accepted": 0, "ignored": 0, "scrobbles": []}

    if len(tracks) > 50:
        raise ValueError("Cannot scrobble more than 50 tracks in a single batch")

    params: dict[str, str] = {
        "method": "track.scrobble",
        "api_key": LASTFM_API_KEY,
        "sk": session_key,
    }

    for i, t in enumerate(tracks):
        params[f"artist[{i}]"] = t.artist
        params[f"track[{i}]"] = t.track
        params[f"timestamp[{i}]"] = str(t.timestamp)
        if t.album:
            params[f"album[{i}]"] = t.album
        if t.track_number:
            params[f"trackNumber[{i}]"] = str(t.track_number)
        if t.duration > 0:
            params[f"duration[{i}]"] = str(t.duration)
        if t.mbid:
            params[f"mbid[{i}]"] = t.mbid

    res = call_api(params, is_post=True)
    scrobbles = res.get("scrobbles", {})
    attr = scrobbles.get("@attr", {})

    accepted = int(attr.get("accepted", 0))
    ignored = int(attr.get("ignored", 0))

    return {
        "accepted": accepted,
        "ignored": ignored,
        "raw": scrobbles,
    }


def scrobble_tracks(
    session_key: str,
    tracks: list[ScrobbleEntry],
    batch_delay: float = 0.25,
) -> dict[str, Any]:
    """Submit all valid tracks to Last.fm in sequential batches of 50.

    Halts immediately if any batch fails to ensure unsubmitted tracks are not lost.
    """
    total_accepted = 0
    total_ignored = 0
    batches_count = (len(tracks) + 49) // 50

    for b in range(batches_count):
        chunk = tracks[b * 50 : (b + 1) * 50]
        res = scrobble_batch(session_key, chunk)
        total_accepted += res["accepted"]
        total_ignored += res["ignored"]

        if b + 1 < batches_count and batch_delay > 0:
            time.sleep(batch_delay)

    return {
        "accepted": total_accepted,
        "ignored": total_ignored,
        "total": len(tracks),
    }
