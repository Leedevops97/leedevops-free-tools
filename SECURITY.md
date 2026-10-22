# Security

Report security issues privately to **lx.iwtfree@gmail.com**. Include the tool
version and a minimal synthetic reproduction. Do not send SSH keys, passwords,
payment credentials or full unredacted server reports.

The standalone Server Lens CLI reads local system information only. It does not query public
Internet services, start listeners, change privileges, repair systems or modify
configuration. Optional time-query utilities can communicate with a local
time daemon over a Unix socket or loopback connection. It trusts system
binaries found in PATH, like other shell tools;
use a trusted PATH, especially when choosing to run with sudo. Output strips
terminal control bytes from external text before rendering.

Server Lens Web is a separate, opt-in systemd installation. Its installer
downloads checksum-pinned official components from GitHub and needs root.
Its three listeners bind to loopback; use an SSH tunnel. There is no login or
tenant isolation. Do not expose these ports through a public reverse proxy.
The gateway permits only fixed resource queries, validates local Host headers,
caps response sizes and concurrency, and does not provide a raw PromQL proxy.
Real telemetry stays on your own server. Public demo assets use simulated
data without requesting any metrics API. The API omits host labels, login
records, user names and IP addresses. Review the web tool's README for storage,
resource limits and the scope of testing; this is not a security audit.

Initial release: 1.0.0. There is no guaranteed response-time commitment or
third-party audit. Review the source before running on sensitive systems.
