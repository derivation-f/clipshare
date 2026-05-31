"""
HTTP server that receives text via POST /clip and copies it to the clipboard.
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

import clipboard_util


class ClipShareHandler(BaseHTTPRequestHandler):
    """Handles POST /clip (receive text), GET /health, and GET / (status page)."""

    # Set by the serve() function before starting the server
    server_config: dict = {}
    hostname: str = ""

    def log_message(self, format, *args):
        """Suppress default stderr logging; print in our own format."""
        pass  # We handle logging ourselves via print()

    def _check_auth(self) -> bool:
        """Return True if the request is authorized (or auth is disabled)."""
        secret = self.server_config.get("secret")
        if not secret:
            return True
        auth_header = self.headers.get("Authorization", "")
        expected = f"Bearer {secret}"
        return auth_header == expected

    def _read_body(self) -> dict | None:
        """Read and parse the JSON body. Returns None on failure."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return None

        max_bytes = self.server_config.get("max_size_kb", 512) * 1024
        if content_length > max_bytes:
            self.send_error(413, f"Payload too large (max {max_bytes // 1024}KB)")
            return None

        try:
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "Invalid JSON")
            return None

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (
                "<html><body><h1>ClipShare Server</h1>"
                f"<p>Host: {self.hostname}</p>"
                "<p>Ready to receive.</p>"
                "</body></html>"
            )
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/clip":
            self.send_error(404)
            return

        if not self._check_auth():
            self.send_error(403, "Forbidden: invalid or missing secret")
            return

        data = self._read_body()
        if data is None:
            self.send_error(400, "No data provided")
            return

        text = data.get("text", "")
        source = data.get("source_host", "unknown")

        if not text:
            self.send_error(400, "Empty text")
            return

        try:
            clipboard_util.copy(text)
            print(f"[{self.log_date_time_string()}] Received {len(text)} chars from {source} → clipboard")
        except Exception as e:
            print(f"[ERROR] Clipboard copy failed: {e}", file=sys.stderr)
            self.send_error(500, f"Clipboard error: {e}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        resp = {"status": "copied", "size": len(text)}
        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def do_POST_redirect(self):
        """Handle POST requests that don't match /clip."""
        self.send_error(404)


def serve(config: dict) -> None:
    """Start the HTTP server. Blocks until Ctrl+C."""
    import socket
    hostname = socket.gethostname()
    port = config["port"]

    server = HTTPServer(("0.0.0.0", port), ClipShareHandler)
    server.RequestHandlerClass.server_config = config
    server.RequestHandlerClass.hostname = hostname

    # Get local IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except OSError:
        local_ip = "127.0.0.1"

    print(f"ClipShare server running on http://{local_ip}:{port}")
    print(f"Hostname: {hostname}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
