# Leedevops Free Tools

Small, understandable, free and open-source tools for people who run Linux.

Website: [leeimages.com](https://www.leeimages.com/) · [中文说明](docs/README.zh-CN.md) · [MIT license](LICENSE)

## Server Lens Web 1.1.0

A lightweight Prometheus + Node Exporter dashboard with four resource cards
and one chart. CPU, memory, root-disk capacity and uptime, with English/Chinese
interface, 30-second collection and 48-hour local history. Private live access
uses an SSH tunnel; the public demo is clearly simulated.

[Web edition documentation](tools/server-lens-web/README.md) ·
[Product and demo](https://www.leeimages.com/server-lens-web/)

The web edition installs systemd services and official upstream components;
its requirements and resource limits differ from the standalone CLI below.

## Server Lens 1.0.0

A read-only Linux health dashboard in a single POSIX shell script. No Python,
Node, web server, root requirement, background agent or outbound Internet requests.
Optional time-query utilities may communicate with a time daemon on the same
machine using a local socket or loopback connection.

- Recent login records and their times; current utmp sessions.
- A one-second CPU usage sample, logical processors, model and load averages.
- Available/used memory, swap and separate cgroup resource limits when readable.
- Non-tmpfs filesystem space and usage (up to 20 mounts).
- Local/UTC time and synchronization evidence from chrony, ntpd or systemd.
- A clean terminal dashboard, optional refresh, JSON output and redaction.

```sh
# After cloning or extracting a release:
sh tools/server-lens/server-lens
sh tools/server-lens/server-lens --watch --interval 5
sh tools/server-lens/server-lens --json
sh tools/server-lens/server-lens --json --redact
```

No installation is needed. Inspect the script before running it. To keep a
private report on disk, use `umask 077` before shell redirection. For protected
login records you may choose to run the same inspected script with `sudo`.
There is no auto-install, auto-repair or clock-changing command.

## What results mean

`synchronized` means the configured local time client reports synchronization;
it does not certify an independent Internet time measurement or that the source
is trustworthy. `local-reference` is explicitly not external synchronization.
`unknown` is shown when no usable evidence is available. NTP being enabled alone
is not treated as synchronized.

Login history depends on the system's logging configuration, permissions and
retention. `last`/`wtmpdb` is preferred; fallbacks read up to 200 recent sshd
journal records or the last 500 auth-log lines and show successful SSH logins
only. Missing history never means there were no logins. Current utmp sessions
do not include every non-interactive SSH connection. On older `last` variants,
date precision is limited to what that command provides.

CPU and memory from `/proc` are kernel-visible. In containers they may describe
the host. Readable cgroup limits are shown separately and are not a complete
reconstruction of nested quotas/cpusets. Disk usage excludes tmpfs/devtmpfs;
this is a basic status tool, not an audit, malware detector or full monitoring
platform. Resource labels are simple hints: CHECK at 80%, HIGH at 95%.

## Compatibility and footprint

Requires Linux with readable `/proc`, POSIX `/bin/sh`, `awk`, `uname`, `date`,
`sleep` and standard text utilities. `df`, `last`, `wtmpdb`, `who`, `chronyc`,
`ntpq`, `timedatectl`, `journalctl` and `timeout` are detected at runtime.
Missing optional commands degrade gracefully. External probes are limited to
four seconds when `timeout` exists. Without it, an underlying system command
may take longer. Live refresh takes the collection time plus the chosen pause.

Designed for Debian/Ubuntu, RHEL-family and Alpine/BusyBox systems, on common
Linux architectures. See [the test report](docs/TESTING.md) for environments
actually tested; not every distribution or CPU architecture has been verified.
Runtime measurements and their scope are recorded there, rather than a fixed
memory guarantee for every operating system.

Terminal output is ASCII, uses color only on a suitable TTY, respects
`NO_COLOR`, and is constrained to 40–120 columns. Long login entries wrap.
Piped output has no terminal control codes. `--plain` disables color and watch
redrawing; `--json` is intended for scripts and cannot be combined with watch.
`--redact` masks hostname, complete login/session lines and filesystem paths;
review any report before sharing it. No telemetry is collected.

## Repository layout

Each future free tool belongs under `tools/<tool-name>/` with its own README
and version. This repository contains free tools only; paid work is separate.

```text
tools/server-lens/server-lens   Executable source (run with sh)
tools/server-lens/README.md     Quick start and release notes
tests/                        Deterministic edge-case tests
docs/                         Chinese guide, testing and design notes
```

Run `python3 -m unittest discover -s tests -v` on a Linux development machine.
Python is a test dependency only. Fixtures use `SERVER_LENS_PROC_ROOT` and
`SERVER_LENS_CGROUP_ROOT`; reports with overrides are explicitly marked
`data_source: fixture`. Ordinary users should leave both unset.

## Contribute

Please read [CONTRIBUTING.md](CONTRIBUTING.md). For vulnerabilities, use the
private contact in [SECURITY.md](SECURITY.md), not a public report containing
credentials or real server logs. Tool usage support:
[lx.iwtfree@gmail.com](mailto:lx.iwtfree@gmail.com).
