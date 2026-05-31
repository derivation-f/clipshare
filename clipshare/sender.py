#!/usr/bin/env python3
"""
ClipShare Sender — 发送端程序
将文本内容快速发送到接收端电脑。

Usage:
    python sender.py --clip              发送当前剪贴板内容
    python sender.py "报错信息"            发送指定文本
    python sender.py --file error.log     发送文件内容
    cat error.txt | python sender.py --stdin  管道输入

    python sender.py --status            检查接收端是否在线
    python sender.py --config            显示当前配置
    python sender.py --peer 192.168.1.x --clip   手动指定接收端 IP
"""

import argparse
import socket
import sys

import config
import clipboard_util
import client
import discovery


def get_target(cfg: dict, peer_arg: str | None = None, verbose: bool = True) -> tuple[str, int] | None:
    """
    Resolve the target (host, port).
    Priority: --peer flag > mDNS discovery > config peer_host.
    """
    port = cfg["port"]

    if peer_arg:
        if verbose:
            print(f"Using specified peer: {peer_arg}:{port}")
        return (peer_arg, port)

    if verbose:
        print("Searching for peer via mDNS...")
    discovered = discovery.discover_peer(timeout=3.0)
    if discovered:
        host, _, hname = discovered
        if verbose:
            print(f"Found peer: {hname} ({host}:{port})")
        return (host, port)

    host = config.get_peer(cfg)
    if host:
        if verbose:
            print(f"Using configured peer: {host}:{port}")
        return (host, port)

    return None


def cmd_send(args):
    """Send text to the peer."""
    cfg = config.load()

    # --- Gather text ---
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
            print(f"Cannot read {args.file} as UTF-8 text.")
            sys.exit(1)
        if not text:
            print(f"File is empty: {args.file}")
            sys.exit(1)
    else:
        text = args.text
        if not text:
            print("No text provided. Use --clip, --file, --stdin, or pass text directly.")
            print("Examples:")
            print("  python sender.py --clip")
            print("  python sender.py \"error message here\"")
            print("  python sender.py --file error.log")
            sys.exit(1)

    # --- Size check ---
    max_kb = cfg.get("max_size_kb", 512)
    if len(text.encode("utf-8")) > max_kb * 1024:
        print(f"Text too large ({len(text.encode('utf-8')) // 1024}KB > {max_kb}KB limit).")
        print(f"Increase max_size_kb in clipshare.json or trim the content.")
        sys.exit(1)

    # --- Resolve target ---
    target = get_target(cfg, peer_arg=args.peer)
    if not target:
        print("No peer found via mDNS and no peer_host configured.")
        print("Options:")
        print("  1. Make sure 'receiver.py' is running on the other machine")
        print("  2. Or set peer_host in clipshare.json")
        print("  3. Or use: python sender.py --peer <IP> --clip")
        sys.exit(1)

    host, port = target

    # --- Send ---
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
    target = get_target(cfg, peer_arg=args.peer)

    if not target:
        print("No peer found.")
        sys.exit(1)

    host, port = target

    import urllib.request
    url = f"http://{host}:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            if resp.status == 200 and resp.read().decode().strip() == "ok":
                print("Peer is online and reachable.")
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
        description="ClipShare Sender — 发送文本到接收端电脑"
    )

    # Mutually exclusive: send modes + status + config
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--clip", action="store_true", help="发送当前剪贴板内容")
    action.add_argument("--file", metavar="PATH", help="发送文件内容")
    action.add_argument("--stdin", action="store_true", help="从标准输入读取")
    action.add_argument("--status", action="store_true", help="检查接收端是否在线")
    action.add_argument("--config", action="store_true", help="显示当前配置")

    parser.add_argument("text", nargs="?", help="要发送的文本（不使用 --clip/--file/--stdin 时）")
    parser.add_argument("--peer", metavar="HOST", help="手动指定接收端 IP/主机名")

    args = parser.parse_args()

    if args.status:
        cmd_status(args)
    elif args.config:
        cmd_config(args)
    else:
        cmd_send(args)


if __name__ == "__main__":
    main()
