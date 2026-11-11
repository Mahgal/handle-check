# Sample output — real live run

Command: `python -m handle_check octocat --json`

Run on 2026-11-11 from this VM (Python 3.12.3, network available).
Exit code: **0** — all five services answered.

```json
{
  "name": "octocat",
  "results": [
    {
      "service": "github",
      "name": "octocat",
      "status": "taken",
      "detail": "user exists (HTTP 200)"
    },
    {
      "service": "npm",
      "name": "octocat",
      "status": "taken",
      "detail": "package exists (HTTP 200)"
    },
    {
      "service": "pypi",
      "name": "octocat",
      "status": "taken",
      "detail": "project exists (HTTP 200)"
    },
    {
      "service": "dockerhub",
      "name": "octocat",
      "status": "taken",
      "detail": "namespace exists (HTTP 200)"
    },
    {
      "service": "gitlab",
      "name": "octocat",
      "status": "available",
      "detail": "no matching user (empty list)"
    }
  ]
}
```

Note: a second live run seconds later (plain table output) hit GitHub's
unauthenticated rate limit — GitHub returned HTTP 403, which the tool
correctly reported as `unknown` (exit code 1) instead of guessing the
handle was free. Unauthenticated GitHub API calls are rate-limited to
60/hour per IP, so occasional `unknown` results on GitHub are expected
when the tool is run repeatedly without a token.
