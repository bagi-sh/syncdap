"""Configuration reader and precedence resolver for syncdap."""

import os
from pathlib import Path
from typing import Any


def get_config_dir() -> Path:
    env_cfg = os.environ.get("SYNCDAP_CONFIG_FILE")
    if env_cfg:
        return Path(env_cfg).expanduser().resolve().parent
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
    env_cfg = os.environ.get("SYNCDAP_CONFIG_FILE")
    if env_cfg:
        return Path(env_cfg).expanduser().resolve()
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
    config: dict[str, str] = {}
    p = get_config_path()
    if p.is_file():
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    clean_k = k.strip()
                    clean_v = v.strip()
                    config[clean_k] = clean_v
                    config[clean_k.replace("-", "_")] = clean_v
                    config[clean_k.replace("_", "-")] = clean_v
        except Exception:
            pass
    return config


def get_config_value(key: str, default: str | None = None) -> str | None:
    cfg = load_config()
    if key in cfg:
        return cfg[key]
    norm_under = key.replace("-", "_")
    if norm_under in cfg:
        return cfg[norm_under]
    norm_hyphen = key.replace("_", "-")
    if norm_hyphen in cfg:
        return cfg[norm_hyphen]
    return default


def _cast_setting_value(val_str: str, val_type: type, fallback: Any) -> Any:
    if val_type is bool:
        return val_str.lower() in ("true", "1", "yes", "on", "enable", "enabled")
    if val_type is int:
        try:
            return int(val_str)
        except (ValueError, TypeError):
            return fallback
    if val_type is float:
        try:
            return float(val_str)
        except (ValueError, TypeError):
            return fallback
    return val_str


def resolve_setting(
    env_vars: str | list[str] | tuple[str, ...] | None,
    config_keys: str | list[str] | tuple[str, ...] | None,
    default: Any,
    val_type: type = str,
) -> Any:
    """Resolve a configuration parameter enforcing strict precedence:

    1: CLI flag / explicit environment override (highest priority)
    2: Local configuration file (~/.config/syncdap/config, etc.)
    3: Installation default (lowest priority)
    """
    # Level 1: CLI flag / Environment override
    if env_vars:
        vars_list = [env_vars] if isinstance(env_vars, str) else list(env_vars)
        for var in vars_list:
            env_val = os.environ.get(var)
            if env_val is not None and env_val.strip() != "":
                return _cast_setting_value(env_val.strip(), val_type, default)

    # Level 2: Local configuration file
    if config_keys:
        keys_list = [config_keys] if isinstance(config_keys, str) else list(config_keys)
        for key in keys_list:
            cfg_val = get_config_value(key)
            if cfg_val is not None and cfg_val.strip() != "":
                return _cast_setting_value(cfg_val.strip(), val_type, default)

    # Level 3: Installation default
    return default

