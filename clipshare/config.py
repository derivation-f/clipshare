"""
ClipShare configuration: reads/writes clipshare.json with defaults and env var overrides.
"""

import json
import os
import secrets
from pathlib import Path

DEFAULT_CONFIG = {
    "port": 9876,
    "secret": None,
    "peer_host": None,
    "max_size_kb": 512,
}

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_PATH = CONFIG_DIR / "clipshare.json"


def _env(var: str):
    """Read an environment variable override. Supports CLIPSHARE_PORT, CLIPSHARE_SECRET, CLIPSHARE_PEER_HOST, CLIPSHARE_MAX_SIZE_KB."""
    return os.environ.get(f"CLIPSHARE_{var}")


def load() -> dict:
    """Load config from clipshare.json; create with defaults if it doesn't exist."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            print(f"Warning: {CONFIG_PATH} is invalid, using defaults.")
            cfg = {}
    else:
        cfg = {}

    # Merge with defaults for any missing keys
    merged = {**DEFAULT_CONFIG, **{k: v for k, v in cfg.items() if k in DEFAULT_CONFIG}}

    # Environment variable overrides
    port = _env("PORT")
    if port is not None:
        merged["port"] = int(port)

    secret = _env("SECRET")
    if secret is not None:
        merged["secret"] = secret

    peer = _env("PEER_HOST")
    if peer is not None:
        merged["peer_host"] = peer

    max_size = _env("MAX_SIZE_KB")
    if max_size is not None:
        merged["max_size_kb"] = int(max_size)

    return merged


def save(cfg: dict) -> None:
    """Persist config to clipshare.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def ensure_secret(cfg: dict) -> str:
    """Generate and save a shared secret if one isn't set already."""
    if not cfg.get("secret"):
        cfg["secret"] = secrets.token_hex(16)
        save(cfg)
    return cfg["secret"]


def get_peer(cfg: dict) -> str | None:
    """Return the configured peer address, if any."""
    return cfg.get("peer_host") or None


def get_self_info(cfg: dict) -> tuple[str, int]:
    """Return (local_ip, port) for this machine."""
    import socket
    try:
        # Get the local IP used to reach the outside world
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "127.0.0.1"
    return ip, cfg["port"]
