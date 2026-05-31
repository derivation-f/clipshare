"""
mDNS service registration (server side) and peer discovery (client side)
via zeroconf. Falls back to static IP from config.
"""

import socket
import sys
import time

try:
    from zeroconf import (
        Zeroconf,
        ServiceInfo,
        ServiceBrowser,
        ServiceListener,
        NonUniqueNameException,
    )
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False
    Zeroconf = None  # type: ignore
    ServiceInfo = None  # type: ignore
    ServiceBrowser = None  # type: ignore
    ServiceListener = object  # type: ignore
    NonUniqueNameException = Exception  # type: ignore


SERVICE_TYPE = "_clipshare._tcp.local."
SERVICE_NAME = "ClipShare"


def _get_local_ip() -> str:
    """Get the primary local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# --- Server-side: mDNS registration ---

_zc: Zeroconf | None = None
_service_info: ServiceInfo | None = None


def register_service(port: int) -> None:
    """Register this machine as a ClipShare service on mDNS.

    If the default service name conflicts with another on the network,
    automatically appends a suffix to make it unique.
    If registration fails entirely, prints a warning but does not crash —
    the receiver will still work with manual peer_host configuration.
    """
    if not HAS_ZEROCONF:
        print("[discovery] zeroconf not installed. Install with: pip install zeroconf")
        print("[discovery] Falling back to static peer_host in clipshare.json")
        return

    global _zc, _service_info

    ip = _get_local_ip()
    hostname = socket.gethostname()
    base_name = f"{hostname}.{SERVICE_TYPE}"

    _zc = Zeroconf()

    # Try the base name first, then append -2, -3, etc. on conflict
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            svc_name = base_name
        else:
            svc_name = f"{hostname}-{attempt}.{SERVICE_TYPE}"

        try:
            _service_info = ServiceInfo(
                SERVICE_TYPE,
                svc_name,
                addresses=[socket.inet_aton(ip)],
                port=port,
                properties={"hostname": hostname, "version": "1.0"},
            )
            _zc.register_service(_service_info)
            print(f"[discovery] Registered mDNS service: {svc_name} → {ip}:{port}")
            return
        except NonUniqueNameException:
            if _service_info:
                try:
                    _zc.unregister_service(_service_info)
                except Exception:
                    pass
            if attempt == max_attempts:
                print(f"[discovery] Warning: Could not register unique mDNS name after {max_attempts} attempts.")
                print("[discovery] Receiver is running but auto-discovery may not work.")
                print("[discovery] Use manual peer_host in clipshare.json instead.")
                return
            continue
        except Exception as e:
            print(f"[discovery] Warning: mDNS registration failed: {e}")
            print("[discovery] Receiver is running but auto-discovery may not work.")
            print("[discovery] Use manual peer_host in clipshare.json instead.")
            return


def unregister_service() -> None:
    """Unregister the mDNS service. Call on shutdown."""
    global _zc, _service_info
    if _zc and _service_info:
        _zc.unregister_service(_service_info)
        _zc.close()
        _zc = None
        _service_info = None


# --- Client-side: mDNS discovery ---

class _ClipShareListener(ServiceListener):
    """Listens for _clipshare._tcp.local. services and collects results."""

    def __init__(self):
        self.peers: list[dict] = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            ip = socket.inet_ntoa(info.addresses[0]) if info.addresses else None
            hostname = info.properties.get(b"hostname", b"unknown").decode("utf-8")
            self.peers.append({
                "hostname": hostname,
                "ip": ip,
                "port": info.port,
            })

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass  # Not needed for discovery

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


def discover_peer(timeout: float = 3.0) -> tuple[str, int, str] | None:
    """
    Discover a ClipShare peer via mDNS.
    Returns (ip, port, hostname) or None if not found.
    """
    if not HAS_ZEROCONF:
        return None

    zc = Zeroconf()
    listener = _ClipShareListener()
    browser = ServiceBrowser(zc, SERVICE_TYPE, listener)

    # Wait for discovery, checking every 100ms
    deadline = time.time() + timeout
    while time.time() < deadline:
        if listener.peers:
            peer = listener.peers[0]
            zc.close()
            return (peer["ip"], peer["port"], peer["hostname"])
        time.sleep(0.1)

    zc.close()
    return None
