# Server Lens 1.0.0 — testing

Tested on 2026-10-22. No dependencies or container images were downloaded to
the production server for these checks; existing images were reused.

| Environment | What actually passed |
|---|---|
| Ubuntu 26.04, x86_64, Linux 7.0 | sh/dash/bash syntax and real JSON snapshots; chrony evidence and successful-SSH journal fallback |
| Debian GNU/Linux 13 (existing WordPress container) | Real JSON snapshot as the unprivileged www-data user; unavailable logs/time services degrade gracefully |
| Alpine Linux 3.24, BusyBox 1.37 ash/awk | Real JSON snapshot in an isolated container with no network, read-only filesystem and all capabilities dropped |
| Ubuntu pseudo-terminal | Colored dashboard, watch refresh entry, Ctrl+C exit code 130 and cursor restoration |

Containers share the host kernel. These are userspace/shell compatibility
checks, not three independent kernel or architecture tests. RHEL-family and
ARM systems are design targets but have not yet been run locally.

24 deterministic regression tests passed. They cover CPU guest accounting,
legacy memory estimation/clamping, swap, cgroup v1/v2/unlimited values,
paths with spaces, common tmpfs filtering, missing probes, enabled-but-unsynced
NTP, chrony local/selected/unsynced references, ntpd selection, modern wtmpdb,
successful-SSH-only journal fallback, JSON escaping, terminal control stripping,
redaction, missing CPU samples, narrow terminals, option validation and fixtures.

An early legacy-memory fallback bug was found by the tests and fixed before
release. Complete tests were rerun after the fix. GitHub CI is configured to
repeat Linux regressions and a BusyBox check; its live run status is separate
from these completed server-side tests.

## Observed footprint

One representative Ubuntu snapshot, including optional chrony/journal probes:

| Mode | Wall time | Child-process CPU time | Sampled process-tree RSS peak |
|---|---:|---:|---:|
| JSON + redaction | 1.466 s | 0.064 s | 22,864 KiB |
| Plain dashboard + redaction | 1.359 s | 0.063 s | 22,800 KiB |

Wall time includes the deliberate one-second CPU sample. RSS was sampled every
10ms across the tool and descendants. It sums process RSS (including shared
mapped pages) and can miss short peaks. This is an observation on one machine,
not a guaranteed memory ceiling or an aggregate throughput benchmark. The
measurement process is outside the tool. No daemon remains after exit.

No unredacted server reports or real login records are included in this repo.

## Web edition 1.1.0

The separate opt-in Prometheus web edition has 16 additional gateway tests:
missing/stale samples, failed collectors and upstream outages, nonfinite values,
cache reuse, query/range allowlists, Host validation and response headers.
The live deployment was exercised on Ubuntu 26.04 / x86_64 with the pinned
Prometheus and Node Exporter versions. All three services bind to loopback.
ARM64 release checksums are pinned, but ARM64 and RHEL-family deployment have
not been exercised. See [web documentation](../tools/server-lens-web/README.md).

Browser checks cover English/Chinese, metric and time-range switching,
pause/resume/manual refresh, mobile/tablet layouts and the explicitly simulated
public demo. The demo must not request the live metrics API. No actual server
telemetry or production screenshots are published in this repository.

## Technical references

- [Linux procfs](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
- [systemd timedatectl](https://www.freedesktop.org/software/systemd/man/latest/timedatectl.html)
- [chronyc tracking](https://chrony-project.org/doc/4.2/chronyc.html)
- [wtmpdb transition](https://wiki.debian.org/pam_lastlog2%20and%20wtmpdb)
