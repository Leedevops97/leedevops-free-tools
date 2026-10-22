# Security

Report security issues privately to **lx.iwtfree@gmail.com**. Include the tool
version and a minimal synthetic reproduction. Do not send SSH keys, passwords,
payment credentials or full unredacted server reports.

Server Lens reads local system information only. It does not query public
Internet services, start listeners, change privileges, repair systems or modify
configuration. Optional time-query utilities can communicate with a local
time daemon over a Unix socket or loopback connection. It trusts system
binaries found in PATH, like other shell tools;
use a trusted PATH, especially when choosing to run with sudo. Output strips
terminal control bytes from external text before rendering.

Initial release: 1.0.0. There is no guaranteed response-time commitment or
third-party audit. Review the source before running on sensitive systems.
