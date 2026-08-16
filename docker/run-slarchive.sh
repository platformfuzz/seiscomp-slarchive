#!/bin/bash
set -euo pipefail

export SEISCOMP_ROOT="${SEISCOMP_ROOT:-/home/sysop/seiscomp}"
export PATH="$SEISCOMP_ROOT/bin:$PATH"

mkdir -p "$SEISCOMP_ROOT/var/run"

if [ -f /docker/apply-station-set.py ]; then
  python3 /docker/apply-station-set.py
fi

host="${SEEDLINK_HOST:-seedlink}"
port="${SEEDLINK_PORT:-18000}"
cfg="$SEISCOMP_ROOT/etc/slarchive.cfg"

if [ -f "$cfg" ]; then
  python3 - "$cfg" "$host" "$port" <<'PY'
import pathlib, sys
path, host, port = sys.argv[1:]
text = pathlib.Path(path).read_text() if pathlib.Path(path).exists() else ""
keys = {"address": host, "port": port}
seen = set()
out = []
for line in text.splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in line:
        out.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in keys:
        out.append(f"{key} = {keys[key]}")
        seen.add(key)
    else:
        out.append(line)
for key, val in keys.items():
    if key not in seen:
        out.append(f"{key} = {val}")
pathlib.Path(path).write_text("\n".join(out) + "\n")
PY
fi

echo "waiting for ${host}:${port}..."
ok=0
for _ in $(seq 1 90); do
  if python3 -c "import socket; socket.create_connection(('${host}', int('${port}')), 2).close()" 2>/dev/null; then
    ok=1
    break
  fi
  sleep 2
done
if [ "$ok" != "1" ]; then
  echo "${host}:${port} not reachable" >&2
  exit 1
fi

seiscomp enable slarchive >/dev/null || true
seiscomp update-config slarchive
streams="$SEISCOMP_ROOT/var/lib/slarchive/slarchive.streams"
if [ ! -f "$streams" ]; then
  echo "missing $streams" >&2
  exit 1
fi
sds="${SLARCHIVE_SDS:-$SEISCOMP_ROOT/var/lib/archive}"
mkdir -p "$sds"
echo "starting slarchive -> ${host}:${port} sds $sds"
exec slarchive -SDS "$sds" -Fi:1 -Fc:900 -l "$streams" "${host}:${port}"
