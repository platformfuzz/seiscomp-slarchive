#!/usr/bin/env python3
"""Rewrite station keys and import inventory from env.

Env:
  SEEDLINK_UPSTREAM_HOST / SEEDLINK_UPSTREAM_PORT
  SEEDLINK_NETWORK          default GE
  SEEDLINK_STATIONS         comma list, or * / ALL for every station the
                            upstream SeedLink INFO STATIONS advertises
  SEEDLINK_SELECTORS        chain selectors; * or empty means all streams
  STATION_KEY_BINDINGS      comma-separated key lines (module:profile)
  INVENTORY_FDSN_BASE       e.g. https://service.geonet.org.nz/fdsnws/station/1/query
  INVENTORY_FDSN_LEVEL      default response
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def root() -> Path:
    return Path(os.environ.get("SEISCOMP_ROOT", "/home/sysop/seiscomp"))


def info_stations(host: str, port: int) -> list[tuple[str, str]]:
    s = socket.create_connection((host, port), 20)
    try:
        s.sendall(b"HELLO\r\n")
        s.settimeout(10)
        s.recv(2048)
        s.sendall(b"INFO STATIONS\r\n")
        buf = b""
        s.settimeout(20)
        while True:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if buf.count(b"</seedlink>") >= 1:
                break
    finally:
        s.close()
    pairs = re.findall(br'<station name="([^"]+)" network="([^"]+)"', buf)
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_sta, raw_net in pairs:
        sta, net = raw_sta.decode(), raw_net.decode()
        if not re.fullmatch(r"[A-Za-z0-9]+", sta):
            continue
        if not re.fullmatch(r"[A-Za-z0-9]+", net):
            continue
        key = (net, sta)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def write_profile(host: str, port: str, selectors: str) -> None:
    path = root() / "etc" / "key" / "seedlink" / "profile_geofon"
    if not path.exists():
        return
    lines = []
    seen_sel = False
    for line in path.read_text().splitlines():
        if line.startswith("sources.chain.address"):
            lines.append(f"sources.chain.address = {host}")
        elif line.startswith("sources.chain.port"):
            lines.append(f"sources.chain.port = {port}")
        elif line.startswith("sources.chain.selectors"):
            if selectors:
                lines.append(f"sources.chain.selectors = {selectors}")
            seen_sel = True
        else:
            lines.append(line)
    if selectors and not seen_sel:
        lines.append(f"sources.chain.selectors = {selectors}")
    path.write_text("\n".join(lines) + "\n")


def write_keys(stations: list[tuple[str, str]], bindings: str) -> None:
    keydir = root() / "etc" / "key"
    keydir.mkdir(parents=True, exist_ok=True)
    for old in keydir.glob("station_*"):
        old.unlink()
    text = bindings.strip() + "\n"
    for net, sta in stations:
        (keydir / f"station_{net}_{sta}").write_text(text)
    print(f"wrote {len(stations)} station keys")


def import_inventory(stations: list[tuple[str, str]], base: str, level: str) -> None:
    by_net: dict[str, list[str]] = {}
    for net, sta in stations:
        by_net.setdefault(net, []).append(sta)
    for net, stas in by_net.items():
        for i in range(0, len(stas), 40):
            batch = stas[i : i + 40]
            url = f"{base}?net={net}&sta={','.join(batch)}&level={level}"
            dest = Path(f"/tmp/inv-{net}-{i}.xml")
            print(f"inventory {url}")
            try:
                urllib.request.urlretrieve(url, dest)
            except urllib.error.URLError as exc:
                print(f"inventory fetch failed: {exc}", file=sys.stderr)
                raise
            subprocess.check_call(["seiscomp", "exec", "import_inv", "fdsnxml", str(dest)])
    Path("/tmp/runtime-inventory.ok").write_text("ok\n")


def main() -> int:
    host = os.environ.get("SEEDLINK_UPSTREAM_HOST", "").strip()
    port = os.environ.get("SEEDLINK_UPSTREAM_PORT", "18000").strip()
    network = os.environ.get("SEEDLINK_NETWORK", "").strip()
    stations_env = os.environ.get("SEEDLINK_STATIONS", "").strip()
    selectors = os.environ.get("SEEDLINK_SELECTORS", "BH?.D").strip()
    if selectors in {"*", "ALL", "all"}:
        selectors = ""
    bindings = os.environ.get(
        "STATION_KEY_BINDINGS", "global:all,seedlink:geofon"
    ).replace(",", "\n")
    fdsn_base = os.environ.get("INVENTORY_FDSN_BASE", "").strip()
    fdsn_level = os.environ.get("INVENTORY_FDSN_LEVEL", "response").strip()

    if not (host or network or stations_env or fdsn_base):
        print("apply-station-set: no override env, keeping image keys")
        return 0

    if host:
        write_profile(host, port, selectors)
        print(f"upstream {host}:{port} selectors={selectors or '(all)'}")

    stations: list[tuple[str, str]] = []
    if stations_env in {"*", "ALL", "all"}:
        if not host:
            print("SEEDLINK_STATIONS=* needs SEEDLINK_UPSTREAM_HOST", file=sys.stderr)
            return 1
        advertised = info_stations(host, int(port))
        if network:
            advertised = [p for p in advertised if p[0] == network]
        stations = advertised
        print(f"INFO STATIONS matched {len(stations)} ({network or 'any net'})")
    elif stations_env:
        net = network or "GE"
        stations = [(net, sta.strip()) for sta in stations_env.split(",") if sta.strip()]
    else:
        print("apply-station-set: host/port only, keeping image station keys")
        return 0

    if not stations:
        print("no stations resolved", file=sys.stderr)
        return 1

    write_keys(stations, bindings)
    if fdsn_base:
        import_inventory(stations, fdsn_base.rstrip("?"), fdsn_level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
