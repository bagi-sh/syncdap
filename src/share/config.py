"""Configuration reader for syncdap."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    target = base / "syncdap"
    if target.is_dir():
        return target
    local_target = Path.cwd() / ".config" / "syncdap"
    if local_target.is_dir():
        return local_target
    return target


def get_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    target = base / "syncdap" / "config"
    if target.is_file():
        return target
    local_target = Path.cwd() / ".config" / "syncdap" / "config"
    if local_target.is_file():
        return local_target
    return target


def get_lastfm_session_path() -> Path:
    return get_config_dir() / "lastfm.conf"


def get_scrobbler_state_path() -> Path:
    return get_config_dir() / "scrobbler.state"


def get_scrobbler_log_archive_dir() -> Path:
    return get_config_dir() / "logs"


def load_config() -> dict[str, str]:
    config = {}
    p = get_config_path()
    if p.is_file():
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
        except Exception:
            pass
    return config


def get_config_value(key: str, default: str | None = None) -> str | None:
    return load_config().get(key, default)
