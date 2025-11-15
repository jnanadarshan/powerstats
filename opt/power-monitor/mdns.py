#!/usr/bin/env python3
"""
Lightweight mDNS advertiser using python-zeroconf

This script advertises an `_http._tcp.local.` service with the specified
hostname and port so clients can discover the Power Monitor dashboard as
http://<hostname>.local. It reads settings from config.json via the existing
`config_manager`.
"""
from __future__ import annotations

import logging
import socket
import sys
import time
from pathlib import Path
from typing import List

try:
    from zeroconf import ServiceInfo, Zeroconf
except Exception as e:
    logger = logging.getLogger('mdns')
    logger.error('Missing dependency: python-zeroconf is required to run mdns advertiser. Install via `pip3 install zeroconf`.')
    raise

from config_manager import get_config


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mdns')


def get_local_ips() -> List[str]:
    ips: List[str] = []
    try:
        # Try to get IPv4 addresses for all interfaces via socket
        hostname = socket.gethostname()
        addrs = socket.getaddrinfo(hostname, None, family=socket.AF_INET)
        for a in addrs:
            ip = a[4][0]
            if ip not in ips and not ip.startswith('127.'):
                ips.append(ip)
    except Exception:
        pass
    # Fallback to 0.0.0.0
    if not ips:
        ips = [socket.gethostbyname(socket.gethostname())]
    return ips


def run_mdns(config_path: str | None = None) -> int:
    config = get_config(config_path) if config_path else get_config()

    enabled = config.mdns_enabled
    if not enabled:
        logger.info('mDNS disabled in config; exiting')
        return 0

    hostname = config.mdns_hostname
    port = int(config.mdns_port)

    # Ensure hostname ends in .local when registering
    server = f"{hostname}.local."
    service_type = "_http._tcp.local."
    service_name = f"Power Monitor._http._tcp.local."  # Visible service name

    ips = get_local_ips()
    ipv4 = socket.inet_aton(ips[0]) if ips else socket.inet_aton('0.0.0.0')

    # Build service info
    info = ServiceInfo(
        service_type,
        service_name,
        addresses=[ipv4],
        port=port,
        properties={"path": b"/"},
        server=server,
    )

    zeroconf = Zeroconf()
    try:
        logger.info(f'Registering mDNS service: {service_name} -> {server}:{port}')
        zeroconf.register_service(info)
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info('mDNS advertiser interrupted; unregistering service')
    finally:
        try:
            zeroconf.unregister_service(info)
        except Exception:
            pass
        zeroconf.close()
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Lightweight mDNS announcer')
    parser.add_argument('--config', help='Path to config.json', default=None)
    args = parser.parse_args()
    return run_mdns(args.config)


if __name__ == '__main__':
    sys.exit(main())
