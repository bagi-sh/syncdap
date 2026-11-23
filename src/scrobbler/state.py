"""State, credentials, and log backup management for syncdap scrobbler.

Uses human-readable INI / KEY=VALUE files strictly inside ~/.config/syncdap/.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from share.config import (
    get_config_dir,
    get_lastfm_session_path,
    get_scrobbler_log_archive_dir,
    get_scrobbler_state_path,
)


def load_session() -> dict[str, str] | None:
    """Load Last.fm credentials from ~/.config/syncdap/lastfm.conf."""
    path = get_lastfm_session_path()
    if not path.is_file():
        return None

    session: dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                session[k.strip()] = v.strip()
    except Exception:
        return None

    if "session_key" in session and "username" in session:
        session["key"] = session["session_key"]
        session["name"] = session["username"]
        return session
    if "key" in session and "username" in session:
        session["session_key"] = session["key"]
        session["name"] = session["username"]
        return session
    return None


def save_session(username: str, session_key: str, authenticated_at: int | None = None) -> Path:
    """Save Last.fm credentials with 0600 permissions to ~/.config/syncdap/lastfm.conf."""
    path = get_lastfm_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    auth_time = authenticated_at if authenticated_at is not None else int(time.time())
    lines = [
        "# Last.fm session credentials for syncdap",
        f"username = {username}",
        f"session_key = {session_key}",
        f"authenticated_at = {auth_time}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    return path


def remove_session() -> bool:
    """Remove ~/.config/syncdap/lastfm.conf."""
    path = get_lastfm_session_path()
    if path.is_file():
        try:
            path.unlink()
            return True
        except OSError:
            return False
    return False


def load_state() -> dict[str, int]:
    """Load scrobbler deduplication watermark from ~/.config/syncdap/scrobbler.state."""
    path = get_scrobbler_state_path()
    state = {
        "last_scrobbled_timestamp": 0,
        "total_scrobbled": 0,
    }
    if not path.is_file():
        return state

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k in state:
                    try:
                        state[k] = int(v)
                    except ValueError:
                        pass
    except Exception:
        pass

    return state


def save_state(last_scrobbled_timestamp: int, total_scrobbled: int) -> Path:
    """Save scrobbler deduplication watermark to ~/.config/syncdap/scrobbler.state."""
    path = get_scrobbler_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Last.fm Scrobbler State (deduplication watermark)",
        f"last_scrobbled_timestamp = {last_scrobbled_timestamp}",
        f"total_scrobbled = {total_scrobbled}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def archive_log(log_path: Path) -> Path | None:
    """Archive processed .scrobbler.log to ~/.config/syncdap/logs/scrobbler_YYYY-MM-DD_HHMMSS.log."""
    if not log_path.is_file():
        return None

    archive_dir = get_scrobbler_log_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target_file = archive_dir / f"scrobbler_{timestamp_str}.log"

    try:
        shutil.copy2(log_path, target_file)
        return target_file
    except OSError:
        return None
