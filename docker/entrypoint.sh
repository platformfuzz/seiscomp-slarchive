#!/bin/bash
set -euo pipefail

export SEISCOMP_ROOT="${SEISCOMP_ROOT:-/home/sysop/seiscomp}"
export PATH="$SEISCOMP_ROOT/bin:$PATH"
export LD_LIBRARY_PATH="$SEISCOMP_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="$SEISCOMP_ROOT/lib/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$(id -u)" = 0 ]; then
  mkdir -p "$SEISCOMP_ROOT/var/run" "$SEISCOMP_ROOT/var/lib/seedlink" "$SEISCOMP_ROOT/var/lib/slarchive" \
    "$SEISCOMP_ROOT/var/lib/archive" /home/sysop/.seiscomp
  chown -R sysop:sysop "$SEISCOMP_ROOT/var/run" "$SEISCOMP_ROOT/var/lib" /home/sysop/.seiscomp \
    2>/dev/null || true
  exec runuser -u sysop -- "$0" "$@"
fi

mkdir -p "$SEISCOMP_ROOT/var/run"
exec "$@"
