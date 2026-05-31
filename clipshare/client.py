"""
HTTP client that sends text to a ClipShare server via POST /clip.
"""

import json
import sys
import urllib.request
import urllib.error


def send_text(text: str, host: str, port: int, secret: str | None = None, timeout: float = 5.0) -> tuple[bool, str]:
    """
    Send text to the ClipShare server at host:port.
    Returns (success, message).
    """
    import socket

    url = f"http://{host}:{port}/clip"
    source = socket.gethostname()

    payload = json.dumps({
        "text": text,
        "source_host": source,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    # Add auth header if secret is configured
    if secret:
        req.add_header("Authorization", f"Bearer {secret}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                size = data.get("size", len(text))
                return True, f"Sent {size} chars → {host} ({source})"
            else:
                return False, f"Unexpected response: {resp.status}"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return False, f"Server error {e.code}: {e.reason} — {body}"
    except urllib.error.URLError as e:
        return False, f"Cannot reach {host}:{port} — {e.reason}. Is 'clipshare serve' running there?"
    except socket.timeout:
        return False, f"Connection to {host}:{port} timed out."
    except Exception as e:
        return False, f"Error: {e}"
