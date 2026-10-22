# Server Lens Web 1.1.0

[中文用户说明书：访问、安装、指标与常见故障](USER-GUIDE.zh-CN.md)

A small browser dashboard backed by **Prometheus + Node Exporter**. Free / MIT
for the Server Lens code. Upstream components retain their Apache-2.0 licenses.
The original standalone Server Lens CLI remains available separately.

Four cards: CPU usage, memory, root-disk capacity and uptime. One switchable
resource chart; 1h/6h/24h ranges; pause, manual refresh and English/Chinese.
Plain HTML/CSS/JavaScript, SVG charts and Python 3 standard library. No Grafana,
pip/npm install, external fonts, trackers or public metrics proxy.

## Install on your own server

Read the installer/config/source first. Supported installer: **Linux with
systemd, Python 3.9+, x86_64 or aarch64**, and normal `/proc` visibility.
The dashboard is designed for a host/VM, not for measuring a container's cgroup
limits. Existing unrelated Prometheus installations are not changed.

```sh
sudo python3 tools/server-lens-web/install.py
```

This command makes explicit system changes: downloads checksum-pinned official
Prometheus and Node Exporter binaries, writes `/opt/leedevops/server-lens-web`,
and creates/enables three `leedevops-*` systemd services. They start at boot.
No credentials or your metrics are sent to Leedevops. Time series stay locally
in `/var/lib/leedevops-prometheus`. Official binary downloads connect to GitHub.
The root-owned binary cache avoids downloading a second time.

From your computer, replace `YOUR_USER` and `YOUR_SERVER`:

```sh
ssh -N -L 18790:127.0.0.1:18790 YOUR_USER@YOUR_SERVER
```

Then open **http://127.0.0.1:18790/**. Keep the SSH session running. Ports 18790,
19090 and 19100 bind only to 127.0.0.1. Do not open them in a security group or
forward them to an anonymous website. Only trusted local users and SSH tunnel
holders should access the private dashboard; the application has no account
system. For direct Prometheus exploration you can separately forward 19090.

The public website demo uses **clearly labelled simulated data only** and
does not connect to this API. The live application never substitutes simulated
values when Prometheus is unavailable.

## Footprint and meaning

- 30-second collection; 48-hour retention; limited collectors and retained
  metric names. No login names, login IPs, processes or arbitrary label browsing.
- 128MB historical-block retention target. **Not a hard directory size cap**:
  Prometheus WAL/head and compaction need extra space. Leave at least 1GB free.
- Service memory caps: Prometheus 256MiB, exporter 64MiB, web 64MiB. These are
  limits, not actual usage promises; limits may need adjustment on large hosts.
- The frontend refreshes every 30s while visible. Results are cached for 25s;
  at most four fixed upstream queries run together. No arbitrary PromQL API.
- CPU is an idle-counter rate over two minutes. Initial CPU history needs at
  least two scrapes. Empty/stale/failed probes show unknown, never fabricated 0%.
- Memory uses MemAvailable (Linux 3.14+). Disk is the root filesystem and uses
  available-to-applications space; reserved blocks count as unavailable.
- If browser refreshing is paused, the last values and their timestamp remain;
  resume/manual refresh requests a new snapshot. Charts reflect sampled data,
  not continuous measurement. Missing history is not interpolated across gaps.

No web-based installation, automated repair or payment is involved.

## Maintenance

```sh
sudo systemctl status leedevops-prometheus leedevops-node-exporter leedevops-server-lens-web
sudo journalctl -u leedevops-prometheus -u leedevops-node-exporter -u leedevops-server-lens-web --since '10 minutes ago'
```

Settings: `/opt/leedevops/server-lens-web/prometheus.yml` and the three unit
files under `/etc/systemd/system/`. Config changes require restarting the
affected service. The installer refuses unmanaged conflicting files and leaves
an existing managed installation unchanged. Upgrades are explicit maintenance
work; do not blindly delete/reinstall over edited settings or monitoring data.

To stop the addon while retaining all code and data:

```sh
sudo systemctl disable --now leedevops-server-lens-web leedevops-prometheus leedevops-node-exporter
```

Manual removal should first inspect installation.json and preserve data or
configuration you need. No destructive uninstall command is run automatically.
The web gateway is built with Python's standard HTTP server for **trusted
loopback/SSH access only**. Public/Internet-facing deployment, tenant isolation,
alerting, TLS, SSO and access roles require a different deployment review.

## Demo and development

`ui/demo.html` is the explicitly marked browser-only simulation; `ui/index.html`
is live mode. Serve `ui/` with a loopback-only static server for demo development.
Live mode uses `python3 server.py`, with the Prometheus URL restricted to
loopback and static asset paths allowlisted. Local hosts are validated to reduce
DNS-rebinding risks. Run repository tests with
`python3 -m unittest discover -s tests -v`.

AMD64 deployment and real queries are tested during release. ARM64 binaries are
checksum-pinned but this release has not been run on ARM or every distribution.
