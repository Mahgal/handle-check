"""CLI for handle-check.

Exit codes:
    0  every service answered (free or taken — either is a real answer)
    1  at least one service unknown (network/error)
    2  usage error
"""

import argparse
import json
import sys

from . import __version__
from .checkers import SERVICES, check_all


def _table(results, name):
    lines = [f"handle: {name}", "", f"{'SERVICE':<10} {'STATUS':<10} DETAIL"]
    for r in results:
        lines.append(f"{r['service']:<10} {r['status']:<10} {r['detail']}")
    n_free = sum(1 for r in results if r["status"] == "available")
    n_unknown = sum(1 for r in results if r["status"] == "unknown")
    lines.append("")
    lines.append(f"{n_free}/{len(results)} services report this handle as available.")
    if n_unknown:
        lines.append(f"WARNING: {n_unknown} service(s) could not be checked (unknown).")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="handle-check",
        description=(
            "Check whether a username/handle is free on GitHub, npm, PyPI, "
            "Docker Hub, and GitLab."
        ),
    )
    parser.add_argument("name", nargs="?", help="handle to check")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of a table")
    parser.add_argument("--version", action="version",
                        version=f"handle-check {__version__}")
    args = parser.parse_args(argv)

    if not args.name:
        parser.print_usage(sys.stderr)
        print("handle-check: error: a handle is required", file=sys.stderr)
        return 2

    results = check_all(args.name)
    if args.json:
        print(json.dumps({"name": args.name, "results": results}, indent=2))
    else:
        print(_table(results, args.name), end="")

    return 1 if any(r["status"] == "unknown" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
