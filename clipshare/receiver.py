#!/usr/bin/env python3
"""
ClipShare Receiver — 接收端程序
运行此程序后，收到来自发送端的文本会自动复制到剪贴板。

Usage:
    python receiver.py
    python receiver.py --port 9877
    python receiver.py --no-mdns
"""

import argparse
import sys

import config
import discovery
import server


def main():
    parser = argparse.ArgumentParser(
        description="ClipShare Receiver — 接收文本并自动复制到剪贴板"
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="监听端口 (默认: 读取 clipshare.json 中的 port)"
    )
    parser.add_argument(
        "--no-mdns", action="store_true",
        help="禁用 mDNS 自动发现（发送端需手动指定 IP）"
    )
    args = parser.parse_args()

    # Load config
    cfg = config.load()

    # Override port if specified
    if args.port:
        cfg["port"] = args.port

    # Ensure a secret exists for auth
    config.ensure_secret(cfg)

    port = cfg["port"]

    # Register mDNS service (unless disabled)
    if not args.no_mdns:
        discovery.register_service(port)

    try:
        server.serve(cfg)
    finally:
        if not args.no_mdns:
            discovery.unregister_service()


if __name__ == "__main__":
    main()
