#!/usr/bin/env python3
"""
ClipShare — Quick text transfer between Mac and Windows on the same LAN.

Usage:
    python clipshare.py serve              Start receiver (copies incoming text to clipboard)
    python clipshare.py send --clip         Send current clipboard content
    python clipshare.py send "some text"    Send literal text
    python clipshare.py send --file err.log Send file contents
    python clipshare.py status              Check if peer is reachable
    python clipshare.py config              Show current configuration
"""

import argparse
import socket
import sys

import config
import clipboard_util
import client
import discovery
import server


def cmd_serve(args):
    """Start the ClipShare HTTP server and register mDNS service."""
    cfg = config.load()

    # Ensure a secret exists
    secret = config.ensure_secret(cfg)
    port = cfg["port"]

    # Register mDNS
    discovery.register_service(port)

    try:
        server.serve(cfg)
    finally:
        discovery.unregister_service()


def cmd_send(args):
    """Send text to the peer."""
    cfg = config.load()

    # Determine the text to send
    if args.clip:
        text = clipboard_util.paste()
        if not text:
            print("Clipboard is empty.")
            sys.exit(1)
    elif args.stdin:
        text = sys.stdin.read()
        if not text:
            print("No input from stdin.")
            sys.exit(1)
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.file}")
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Cannot read {args.file} as UTF-8 text. Is it a binary file?")
            sys.exit(1)
        if not text:
            print(f"File is empty: {args.file}")
            sys.exit(1)
    else:
        text = args.text
        if not text:
            print("No text provided. Use --clip, --file, --stdin, or pass text directly.")
            sys.exit(1)

    # Check size limit
    max_kb = cfg.get("max_size_kb", 512)
    if len(text.encode("utf-8")) > max_kb * 1024:
        print(f"Text too large ({len(text.encode('utf-8')) // 1024}KB > {max_kb}KB limit).")
        print(f"Increase max_size_kb in clipshare.json or trim the content.")
        sys.exit(1)

    # Discover peer
    port = cfg["port"]

    # Try explicit --peer flag first, then mDNS, then config file
    if args.peer:
        host = args.peer
        print(f"Using specified peer: {host}:{port}")
    else:
        print("Searching for peer via mDNS...")
        discovered = discovery.discover_peer(timeout=3.0)
        if discovered:
            host = discovered[0]
            hname = discovered[2]
            print(f"Found peer: {hname} ({host}:{port})")
        else:
            host = config.get_peer(cfg)
            if host:
                print(f"Using configured peer: {host}:{port}")
            else:
                print("No peer found via mDNS and no peer_host configured.")
                print("Options:")
                print("  1. Make sure 'clipshare serve' is running on the other machine")
                print("  2. Or set peer_host in clipshare.json")
                print("  3. Or use: python clipshare.py send --peer <IP> ...")
                sys.exit(1)

    # Send
    secret = cfg.get("secret")
    ok, msg = client.send_text(text, host, port, secret=secret)
    if ok:
        print(msg)
    else:
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Check if the peer is reachable."""
    cfg = config.load()
    port = cfg["port"]

    # Try explicit --peer, then mDNS, then config
    host = None
    hname = "unknown"

    if args.peer:
        host = args.peer
        print(f"Using specified peer: {host}:{port}")
    else:
        discovered = discovery.discover_peer(timeout=2.0)
        if discovered:
            host = discovered[0]
            hname = discovered[2]
            print(f"Found peer via mDNS: {hname} ({host}:{port})")
        else:
            host = config.get_peer(cfg)
            if host:
                print(f"Using configured peer: {host}:{port}")
                hname = host

    if not host:
        print("No peer found.")
        sys.exit(1)

    # Try to reach /health
    import urllib.request
    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            if resp.status == 200 and resp.read().decode().strip() == "ok":
                print(f"Peer is online and reachable.")
            else:
                print(f"Peer responded but with unexpected status: {resp.status}")
    except Exception as e:
        print(f"Peer is unreachable: {e}")
        sys.exit(1)


def cmd_config(args):
    """Display current configuration."""
    cfg = config.load()
    print("ClipShare Configuration:")
    print(f"  Config file:  {config.CONFIG_PATH}")
    print(f"  Port:         {cfg['port']}")
    print(f"  Secret:       {'[set]' if cfg.get('secret') else '[not set]'}")
    print(f"  Peer host:    {cfg.get('peer_host') or '[auto-discover via mDNS]'}")
    print(f"  Max size:     {cfg['max_size_kb']} KB")
    print(f"  Local IP:     {discovery._get_local_ip()}")
    print(f"  Hostname:     {socket.gethostname()}")
    print()
    print("Environment variable overrides:")
    print("  CLIPSHARE_PORT, CLIPSHARE_SECRET, CLIPSHARE_PEER_HOST, CLIPSHARE_MAX_SIZE_KB")


def main():
    parser = argparse.ArgumentParser(
        description="ClipShare — Quick text transfer between Mac and Windows on the same LAN."
    )
    sub = parser.add_subparsers(dest="command", help="Commands")

    # serve
    sub.add_parser("serve", help="Start receiver — copies incoming text to clipboard")

    # send
    send_p = sub.add_parser("send", help="Send text to the other machine")
    send_group = send_p.add_mutually_exclusive_group()
    send_group.add_argument("--clip", action="store_true", help="Send current clipboard content")
    send_group.add_argument("--file", metavar="PATH", help="Send contents of a file")
    send_group.add_argument("--stdin", action="store_true", help="Read from stdin")
    send_p.add_argument("text", nargs="?", help="Text to send (literal string)")
    send_p.add_argument("--peer", metavar="HOST", help="Specify peer IP/hostname directly")

    # status
    status_p = sub.add_parser("status", help="Check if the peer is reachable")
    status_p.add_argument("--peer", metavar="HOST", help="Specify peer IP/hostname directly")

    # config
    sub.add_parser("config", help="Show current configuration")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
