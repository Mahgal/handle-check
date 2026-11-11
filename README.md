# handle-check

Check whether a username/handle is free on GitHub, npm, PyPI, Docker Hub, and GitLab — from one CLI, with one command.

## Quick start

Requires Python 3.12+. Standard library only — no pip installs.

```bash
python -m handle_check octocat
```

```text
handle: octocat

SERVICE    STATUS     DETAIL
github     taken      user exists (HTTP 200)
npm        taken      package exists (HTTP 200)
pypi       taken      project exists (HTTP 200)
dockerhub  taken      namespace exists (HTTP 200)
gitlab     available  no matching user (empty list)

0/5 services report this handle as available.
```

JSON output for scripts:

```bash
python -m handle_check octocat --json
```

```json
{
  "name": "octocat",
  "results": [
    {"service": "github", "name": "octocat", "status": "taken", "detail": "user exists (HTTP 200)"},
    {"service": "npm", "name": "octocat", "status": "taken", "detail": "package exists (HTTP 200)"},
    {"service": "pypi", "name": "octocat", "status": "taken", "detail": "project exists (HTTP 200)"},
    {"service": "dockerhub", "name": "octocat", "status": "taken", "detail": "namespace exists (HTTP 200)"},
    {"service": "gitlab", "name": "octocat", "status": "available", "detail": "no matching user (empty list)"}
  ]
}
```

(The output above is the real result of `python -m handle_check octocat --json`
run on 2026-11-11 from the author's VM; exit code 0. Full transcript in
[`examples/sample-output.md`](examples/sample-output.md).)

## How each service is checked

| Service   | Request | "Free" means |
|-----------|---------|--------------|
| GitHub    | `GET https://api.github.com/users/<name>` | HTTP 404 — no such user |
| npm       | `GET https://registry.npmjs.org/<name>` | HTTP 404 — no such package |
| PyPI      | `GET https://pypi.org/pypi/<name>/json` | HTTP 404 — no such project |
| Docker Hub| `GET https://hub.docker.com/v2/repositories/<name>/` | HTTP 404 — no such namespace |
| GitLab    | `GET https://gitlab.com/api/v4/users?username=<name>` | Empty result list |

Every request uses a 10-second timeout and `User-Agent: handle-check/0.1`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Every service answered (free or taken — either is a real answer) |
| 1 | At least one service was `unknown` (network error, timeout, or an unexpected HTTP status) |
| 2 | Usage error (e.g. no handle given) |

## What "unknown" means

Any HTTP status other than the expected 200/404, a timeout, or a transport
error is reported as `unknown` with the reason — never guessed as free.
For example, unauthenticated GitHub API calls are rate-limited to 60/hour
per IP; a 403 from that limit shows up as `unknown`, not `available`.

## A note on availability

Availability is a point-in-time check. A handle reported as free right now
can be taken a minute later, and a "free" result here does not reserve it
anywhere. Register it promptly if you want it.

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite runs entirely against a local in-process HTTP server with canned
responses — it never touches the live network. See [`SMOKE.md`](SMOKE.md)
for the verification log.
