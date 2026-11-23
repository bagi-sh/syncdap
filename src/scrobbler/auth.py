"""Last.fm Desktop Authentication flow.

Orchestrates token retrieval, browser authorization handoff, terminal polling,
and secure 0600 credential storage in ~/.config/syncdap/lastfm.conf.
"""

import sys
import time
import webbrowser

from src.scrobbler.client import (
    LastFmError,
    TokenPendingError,
    get_session,
    get_token,
)
from src.scrobbler.state import load_session, remove_session, save_session
from src.share.config import get_lastfm_session_path
from src.share.constants import LASTFM_API_KEY
from src.share.icons import ICONS, format_error_dual


def authenticate(force: bool = False, quiet: bool = False) -> dict[str, str] | None:
    """Execute interactive Last.fm Desktop Authentication flow."""
    current = load_session()
    if current and not force:
        username = current.get("username", "unknown")
        if not quiet:
            print(
                f"{ICONS.info} An active Last.fm session already exists for user '{username}'.",
                file=sys.stderr,
            )
        try:
            prompt = f"Overwrite existing session? [y/N]: "
            sys.stderr.write(prompt)
            sys.stderr.flush()
            choice = input().strip().lower()
            if choice not in ("y", "yes"):
                if not quiet:
                    print(f"{ICONS.ok} Keeping existing session.", file=sys.stderr)
                return current
        except (KeyboardInterrupt, EOFError):
            print("\nAuthorization cancelled.", file=sys.stderr)
            return None

    # Step 1: Request temporary token
    if not quiet:
        print(f"{ICONS.info} Requesting authorization token from Last.fm...", file=sys.stderr)
    try:
        token = get_token()
    except LastFmError as e:
        print(
            format_error_dual(
                "Failed to request Last.fm authorization token",
                cause=e.message,
                fix="Check network connectivity and verify Last.fm API service status.",
            ),
            file=sys.stderr,
        )
        return None

    # Step 2: Browser handoff
    auth_url = f"https://www.last.fm/api/auth/?api_key={LASTFM_API_KEY}&token={token}"
    if not quiet:
        print(f"\n{ICONS.arrow} Please authorize Syncdap in your browser:", file=sys.stderr)
        print(f"  {auth_url}\n", file=sys.stderr)

    # Attempt to open browser
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    if not quiet:
        print(f"{ICONS.info} Waiting for authorization (polling every 2.5s, press Ctrl+C to cancel)...", file=sys.stderr)

    # Step 3: Polling loop
    poll_interval = 2.5
    max_attempts = 120  # 5 minutes
    session: dict[str, str] | None = None

    for attempt in range(max_attempts):
        try:
            time.sleep(poll_interval)
            session = get_session(token)
            if session:
                break
        except TokenPendingError:
            # Token not authorized yet or temporary server hiccup, keep polling
            continue
        except LastFmError as e:
            print(
                format_error_dual(
                    "Authorization rejected or expired",
                    cause=e.message,
                    fix="Run 'syncdap scrobbler auth' to restart the authentication process.",
                ),
                file=sys.stderr,
            )
            return None
        except KeyboardInterrupt:
            print("\nAuthorization cancelled by user.", file=sys.stderr)
            return None

    if not session:
        print(
            format_error_dual(
                "Authentication timed out",
                cause="The authorization was not completed within 5 minutes.",
                fix="Run 'syncdap scrobbler auth' and approve the request in your browser promptly.",
            ),
            file=sys.stderr,
        )
        return None

    # Step 4: Persist credentials (chmod 0600)
    saved_path = save_session(session["name"], session["key"])
    if not quiet:
        print(
            f"{ICONS.ok} Authenticated successfully with Last.fm as '{session['name']}'.",
            file=sys.stdout,
        )
        print(f"  Saved session credentials to {saved_path} (mode 0600)", file=sys.stderr)

    return session


def logout(quiet: bool = False) -> bool:
    """Remove local Last.fm credentials."""
    path = get_lastfm_session_path()
    existed = remove_session()
    if not quiet:
        if existed:
            print(f"{ICONS.ok} Logged out of Last.fm. Credentials removed from {path}.")
        else:
            print(f"{ICONS.info} No active Last.fm session found at {path}.")
    return existed
