# Contributing

Keep tools small, read-only by default, and understandable without a service
installation. Prefer POSIX shell and documented, optional command fallbacks.
Do not add telemetry, remote script execution, credentials or real server logs.

For Server Lens, run the Linux unittest suite and `sh -n` with dash, bash and
BusyBox ash when available. Add a regression test for a real parsing or
compatibility issue; keep fixtures synthetic. Describe tested distributions
and architectures accurately. New tools should include their own README and
license information under `tools/<name>/`.

Use pull requests for changes and issues for reproducible non-sensitive bugs.
Include the tool version, distribution, shell, and redacted output if needed.
