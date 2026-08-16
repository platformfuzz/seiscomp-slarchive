# seiscomp-slarchive

![CI](https://github.com/platformfuzz/seiscomp-slarchive/actions/workflows/ci.yml/badge.svg)
![Build and Release](https://github.com/platformfuzz/seiscomp-slarchive/actions/workflows/build-and-release.yml/badge.svg)

Unofficial SeisComP slarchive image built with public gsm. Not gempa-supported.

The process archives SeedLink miniSEED to SDS.

**Package:** [ghcr.io/platformfuzz/seiscomp-slarchive](https://github.com/platformfuzz/seiscomp-slarchive/pkgs/container/seiscomp-slarchive)

## Run

```bash
docker pull ghcr.io/platformfuzz/seiscomp-slarchive:latest
docker run --rm ghcr.io/platformfuzz/seiscomp-slarchive:latest
```

Upstream SeedLink host and port can be overridden with `SEEDLINK_HOST` and `SEEDLINK_PORT`.

SDS files live under `/home/sysop/seiscomp/var/lib/archive`. Mount that path if the archive must survive restarts.

## Build

```bash
docker build -t seiscomp-slarchive:test .
docker run --rm seiscomp-slarchive:test
```
