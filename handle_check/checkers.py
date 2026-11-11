"""Checkers for each service.

Every checker returns a dict::

    {"service": ..., "name": ..., "status": "available"|"taken"|"unknown",
     "detail": "..."}

The "available" verdict is only ever derived from an explicit 404 (or an
empty result list for GitLab). Any other HTTP status, timeout, or transport
error maps to "unknown" with the reason — never guessed as free.

All checkers accept an ``endpoints`` mapping of service -> URL template
with a ``{name}`` placeholder. This is the testability seam: tests point the
templates at a local http.server returning canned responses, so the suite
never touches the live network. Defaults point at the real public APIs.
"""

import json
import urllib.error
import urllib.request

USER_AGENT = "handle-check/0.1"
TIMEOUT = 10

DEFAULT_ENDPOINTS = {
    "github": "https://api.github.com/users/{name}",
    "npm": "https://registry.npmjs.org/{name}",
    "pypi": "https://pypi.org/pypi/{name}/json",
    "dockerhub": "https://hub.docker.com/v2/repositories/{name}/",
    "gitlab": "https://gitlab.com/api/v4/users?username={name}",
}

SERVICES = ("github", "npm", "pypi", "dockerhub", "gitlab")


def _get(url, timeout=TIMEOUT):
    """GET url; returns (status_code, body_bytes) or raises.

    HTTPError is converted to its status/body so callers can distinguish
    404 from other failures. URLError / timeout propagate.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(str(e)) from e


def _result(service, name, status, detail):
    return {"service": service, "name": name, "status": status, "detail": detail}


def check_github(name, endpoints=None):
    """GitHub user: 404 = free, 200 = taken."""
    url = (endpoints or DEFAULT_ENDPOINTS)["github"].format(name=name)
    try:
        code, _ = _get(url)
    except RuntimeError as e:
        return _result("github", name, "unknown", f"request failed: {e}")
    if code == 404:
        return _result("github", name, "available", "no such user (HTTP 404)")
    if code == 200:
        return _result("github", name, "taken", "user exists (HTTP 200)")
    return _result("github", name, "unknown", f"unexpected HTTP {code}")


def check_npm(name, endpoints=None):
    """npm package: 404 = free, 200 = taken."""
    url = (endpoints or DEFAULT_ENDPOINTS)["npm"].format(name=name)
    try:
        code, _ = _get(url)
    except RuntimeError as e:
        return _result("npm", name, "unknown", f"request failed: {e}")
    if code == 404:
        return _result("npm", name, "available", "no such package (HTTP 404)")
    if code == 200:
        return _result("npm", name, "taken", "package exists (HTTP 200)")
    return _result("npm", name, "unknown", f"unexpected HTTP {code}")


def check_pypi(name, endpoints=None):
    """PyPI project: 404 = free, 200 = taken."""
    url = (endpoints or DEFAULT_ENDPOINTS)["pypi"].format(name=name)
    try:
        code, _ = _get(url)
    except RuntimeError as e:
        return _result("pypi", name, "unknown", f"request failed: {e}")
    if code == 404:
        return _result("pypi", name, "available", "no such project (HTTP 404)")
    if code == 200:
        return _result("pypi", name, "taken", "project exists (HTTP 200)")
    return _result("pypi", name, "unknown", f"unexpected HTTP {code}")


def check_dockerhub(name, endpoints=None):
    """Docker Hub namespace: 404 = free, 200 = taken."""
    url = (endpoints or DEFAULT_ENDPOINTS)["dockerhub"].format(name=name)
    try:
        code, _ = _get(url)
    except RuntimeError as e:
        return _result("dockerhub", name, "unknown", f"request failed: {e}")
    if code == 404:
        return _result("dockerhub", name, "available", "no such namespace (HTTP 404)")
    if code == 200:
        return _result("dockerhub", name, "taken", "namespace exists (HTTP 200)")
    return _result("dockerhub", name, "unknown", f"unexpected HTTP {code}")


def check_gitlab(name, endpoints=None):
    """GitLab user search: empty list = free, non-empty = taken."""
    url = (endpoints or DEFAULT_ENDPOINTS)["gitlab"].format(name=name)
    try:
        code, body = _get(url)
    except RuntimeError as e:
        return _result("gitlab", name, "unknown", f"request failed: {e}")
    if code != 200:
        return _result("gitlab", name, "unknown", f"unexpected HTTP {code}")
    try:
        users = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _result("gitlab", name, "unknown", "unparseable response body")
    if isinstance(users, list) and not users:
        return _result("gitlab", name, "available", "no matching user (empty list)")
    if isinstance(users, list):
        return _result("gitlab", name, "taken", f"{len(users)} matching user(s)")
    return _result("gitlab", name, "unknown", "unexpected response shape")


CHECKERS = {
    "github": check_github,
    "npm": check_npm,
    "pypi": check_pypi,
    "dockerhub": check_dockerhub,
    "gitlab": check_gitlab,
}


def check_all(name, endpoints=None, services=SERVICES):
    """Run every checker for ``name``; returns a list of result dicts."""
    endpoints = endpoints or DEFAULT_ENDPOINTS
    return [CHECKERS[s](name, endpoints=endpoints) for s in services]
