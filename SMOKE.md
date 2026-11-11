# SMOKE — verification log

All commands run on 2026-11-11 from `~/workspace/github-factory/2026-11-11/handle-check`
on Python 3.12.3, with real exit codes recorded below.

| # | Command | Exit code | Result |
|---|---------|-----------|--------|
| 1 | `python3 -m unittest discover -s tests -v` | 0 | 23 tests, all passed |
| 2 | `python3 -m handle_check octocat --json` | 0 | All 5 services answered (see `examples/sample-output.md`) |
| 3 | `python3 -m handle_check octocat` | 1 | 4 answered; GitHub returned HTTP 403 (unauthenticated rate limit) → correctly reported `unknown`, not guessed free |
| 4 | `python3 -m handle_check` (no handle) | 2 | Usage error, as specified |

Notes:
- Test suite (command 1) uses only a local in-process `http.server` with
  canned responses; no live network dependency.
- Command 3's exit code 1 is the *specified* behaviour for an unknown
  service, and the GitHub 403 was a genuine rate-limit response from the
  live API — the tool's conservative mapping worked as designed.
